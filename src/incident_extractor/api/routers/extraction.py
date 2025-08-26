"""
Extraction Router

This module provides production-ready incident extraction endpoints for processing
unstructured text and extracting structured information using the LangGraph workflow.

Features:
- Standardized response models with request tracking
- Comprehensive error handling with custom exceptions
- Input validation and sanitization
- Batch processing capabilities
- Performance monitoring and logging
- Business logic separation with dependency injection
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...config import get_logger
from ...graph.workflow import extract_incident_info
from ...models.schemas import ExtractionRequest
from ..dependencies import get_request_id
from ..responses import (
    ExtractionData,
    ExtractionException,
    ExtractionResponse,
    TextValidationException,
    ValidationException,
    WorkflowException,
    create_success_response,
)

# Create router for extraction endpoints with proper prefix
router = APIRouter(prefix="/v1/incidents", tags=["extraction"])

# Set up logger
logger = get_logger("api.extraction")


def _validate_text_input(text: str) -> None:
    """
    Validate text input for extraction.

    Args:
        text: The text to validate

    Raises:
        TextValidationException: If text is invalid
    """
    text_length = len(text.strip())

    if text_length == 0:
        raise TextValidationException(
            detail="Text cannot be empty",
            text_length=0,
        )

    if text_length < 10:
        raise TextValidationException(
            detail=f"Text too short: {text_length} characters (minimum: 10)",
            text_length=text_length,
        )

    if text_length > 5000:
        raise TextValidationException(
            detail=f"Text too long: {text_length} characters (maximum: 5000)",
            text_length=text_length,
        )


def _process_workflow_result(workflow_result: Any) -> dict:
    """
    Process workflow result and extract fields with confidence scores.

    Args:
        workflow_result: Result from the extraction workflow

    Returns:
        dict: Dictionary with processed fields and confidence scores
    """
    extracted_fields = {}
    confidence_scores = {}

    if workflow_result.extracted_data:
        extracted_fields = {
            "data_ocorrencia": workflow_result.extracted_data.data_ocorrencia,
            "local": workflow_result.extracted_data.local,
            "tipo_incidente": workflow_result.extracted_data.tipo_incidente,
            "impacto": workflow_result.extracted_data.impacto,
        }

        for field, value in extracted_fields.items():
            confidence_scores[field] = 1.0 if value is not None else 0.0

    return {"fields": extracted_fields, "scores": confidence_scores}


def _validate_batch_requests(requests: dict[str, ExtractionRequest]) -> None:
    """
    Validate batch request parameters.

    Args:
        requests: Dictionary of batch requests to validate

    Raises:
        ValidationException: If batch validation fails
    """
    if len(requests) == 0:
        raise ValidationException(
            detail="Batch cannot be empty",
            field="requests",
            suggestion="Provide at least one extraction request in the batch",
        )

    if len(requests) > 50:  # Limit batch size for resource management
        raise ValidationException(
            detail=f"Batch size too large: {len(requests)} requests (maximum: 50)",
            field="requests",
            suggestion="Split large batches into smaller chunks of maximum 50 requests",
        )


async def _process_batch_item(
    batch_id: str,
    extraction_request: ExtractionRequest,
    request_id: str,
    endpoint_path: str,
) -> dict:
    """
    Process individual batch request with comprehensive error handling.

    Args:
        batch_id: Identifier for this batch item
        extraction_request: The extraction request to process
        request_id: Base request ID for tracking
        endpoint_path: API endpoint path

    Returns:
        dict: Standardized response for this batch item
    """
    individual_request_id = f"{request_id}-{batch_id}"
    individual_start = time.time()

    try:
        # Validate text using helper function
        _validate_text_input(extraction_request.text)

        # Execute workflow for individual request
        workflow_result = await extract_incident_info(text=extraction_request.text, options=extraction_request.options or {})

        individual_processing_time = (time.time() - individual_start) * 1000

        # Process results using helper function
        result_data = _process_workflow_result(workflow_result)

        extraction_data = ExtractionData(
            extracted_fields=result_data["fields"],
            confidence_scores=result_data["scores"],
            processing_steps=["batch_validation", "workflow_execution", "field_extraction"],
            warnings=None,
        )

        # Create standardized success response
        individual_response = create_success_response(
            data=extraction_data,
            message="Individual extraction completed successfully",
            request_id=individual_request_id,
            processing_time_ms=individual_processing_time,
            endpoint=f"{endpoint_path}/{batch_id}",
        )

        return individual_response.model_dump()

    except (TextValidationException, ValidationException, ExtractionException, WorkflowException) as e:
        individual_processing_time = (time.time() - individual_start) * 1000

        return {
            "status": "error",
            "message": e.detail,
            "data": None,
            "metadata": {
                "request_id": individual_request_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "endpoint": f"{endpoint_path}/{batch_id}",
                "error_code": e.error_code,
                "error_type": e.error_type,
                "processing_time_ms": individual_processing_time,
            },
            "errors": [
                {
                    "error_code": e.error_code,
                    "error_type": e.error_type,
                    "description": e.detail,
                    "field": getattr(e, "field", None),
                    "suggestion": getattr(e, "suggestion", None),
                }
            ],
        }

    except Exception as e:
        individual_processing_time = (time.time() - individual_start) * 1000

        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "data": None,
            "metadata": {
                "request_id": individual_request_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "endpoint": f"{endpoint_path}/{batch_id}",
                "error_code": "UNEXPECTED_ERROR",
                "error_type": "UnexpectedError",
                "processing_time_ms": individual_processing_time,
            },
            "errors": [
                {
                    "error_code": "UNEXPECTED_ERROR",
                    "error_type": "UnexpectedError",
                    "description": f"Unexpected error during processing: {str(e)}",
                    "suggestion": "Contact support if this error persists",
                }
            ],
        }


@router.post("/extract", response_model=ExtractionResponse)
async def extract_incident(
    request: ExtractionRequest,
    http_request: Request,
    request_id: str = Depends(get_request_id),
) -> ExtractionResponse:
    """
    Extract structured incident information from text.

    This endpoint processes a single incident text and returns structured data
    containing incident details with standardized response format.

    Args:
        request: The extraction request containing text and options
        http_request: FastAPI request object for context
        request_id: Unique request identifier for tracking

    Returns:
        ExtractionResponse: Standardized response with extracted incident data

    Raises:
        TextValidationException: If text validation fails
        ExtractionException: If extraction processing fails
        ValidationException: If request validation fails
    """
    start_time = time.time()
    endpoint_path = str(http_request.url.path)

    logger.info(
        "Starting incident extraction",
        extra={
            "request_id": request_id,
            "text_length": len(request.text),
        },
    )

    try:
        # Validate input text using helper function
        _validate_text_input(request.text)

        # Execute extraction workflow
        workflow_result = await extract_incident_info(text=request.text, options=request.options or {})

        # Process workflow result using helper function
        result_data = _process_workflow_result(workflow_result)

        processing_time = (time.time() - start_time) * 1000

        extraction_data = ExtractionData(
            extracted_fields=result_data["fields"],
            confidence_scores=result_data["scores"],
            processing_steps=["text_validation", "workflow_execution", "field_extraction"],
            warnings=None,
        )

        logger.info(
            "Incident extraction completed successfully",
            extra={
                "request_id": request_id,
                "processing_time_ms": processing_time,
                "extracted_fields": list(result_data["fields"].keys()),
            },
        )

        return create_success_response(
            data=extraction_data,
            message="Extraction completed successfully",
            request_id=request_id,
            processing_time_ms=processing_time,
            endpoint=endpoint_path,
        )

    except (TextValidationException, ValidationException, ExtractionException, WorkflowException):
        # Log and re-raise custom exceptions for proper error handling
        processing_time = (time.time() - start_time) * 1000
        logger.warning(
            "Extraction failed with validation or processing error",
            extra={
                "request_id": request_id,
                "processing_time_ms": processing_time,
            },
        )
        raise

    except Exception as e:
        processing_time = (time.time() - start_time) * 1000

        logger.error(
            "Extraction failed with unexpected error",
            extra={
                "request_id": request_id,
                "processing_time_ms": processing_time,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )

        raise ExtractionException(
            detail=f"Extraction failed: {str(e)}",
            suggestion="Check your input text and try again, or contact support",
        ) from e


@router.post("/extract/batch")
async def extract_incidents_batch(
    requests: dict[str, ExtractionRequest],
    http_request: Request,
    request_id: str = Depends(get_request_id),
) -> dict[str, Any]:
    """
    Extract structured incident information from multiple texts in batch.

    This endpoint processes multiple incident texts concurrently for improved performance
    when handling bulk extraction requests with standardized response format.

    Args:
        requests: Dictionary mapping request IDs to extraction requests
        http_request: FastAPI request object for context
        request_id: Unique request identifier for batch tracking

    Returns:
        Dict[str, Any]: Batch processing results with standardized metadata

    Raises:
        ValidationException: If batch validation fails
        ExtractionException: If batch processing encounters critical errors
    """
    start_time = time.time()
    endpoint_path = str(http_request.url.path)

    logger.info(
        "Starting batch extraction",
        extra={
            "request_id": request_id,
            "batch_size": len(requests),
        },
    )

    try:
        # Validate batch using helper function
        _validate_batch_requests(requests)

        # Process all requests using helper function
        results = {}
        success_count = 0

        for batch_id, extraction_request in requests.items():
            result = await _process_batch_item(
                batch_id=batch_id,
                extraction_request=extraction_request,
                request_id=request_id,
                endpoint_path=endpoint_path,
            )

            results[batch_id] = result

            # Count successes for summary
            if isinstance(result, dict) and result.get("status") == "success":
                success_count += 1

        total_processing_time = (time.time() - start_time) * 1000

        # Log batch completion
        logger.info(
            "Batch extraction completed",
            extra={
                "request_id": request_id,
                "processing_time_ms": total_processing_time,
                "batch_size": len(requests),
                "success_count": success_count,
                "failure_count": len(requests) - success_count,
            },
        )

        # Return batch results with standardized format
        return {
            "status": "success",
            "message": f"Batch processing completed: {success_count}/{len(requests)} successful",
            "data": {
                "batch_id": request_id,
                "processing_time_ms": total_processing_time,
                "total_requests": len(requests),
                "successful_requests": success_count,
                "failed_requests": len(requests) - success_count,
                "results": results,
            },
            "metadata": {
                "request_id": request_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "endpoint": endpoint_path,
                "api_version": "1.0.0",
                "processing_time_ms": total_processing_time,
            },
        }

    except (ValidationException, ExtractionException):
        # Re-raise custom exceptions for proper handling
        raise

    except Exception as e:
        total_processing_time = (time.time() - start_time) * 1000

        logger.error(
            "Batch extraction failed with unexpected error",
            extra={
                "request_id": request_id,
                "processing_time_ms": total_processing_time,
                "batch_size": len(requests),
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )

        raise ExtractionException(
            detail=f"Batch processing failed: {str(e)}",
            suggestion="Check batch format and try again, or contact support",
        ) from e


__all__ = ["router"]
