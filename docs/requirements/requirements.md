# Teste Técnico – Engenheiro de IA

## Desafio 1

### O problema

Neste desafio, você deverá criar uma aplicação que utilize um **modelo de linguagem (LLM)** para processar descrições de incidentes e extrair informações estruturadas de forma automática.

A ideia é simular a integração de um LLM em um fluxo de software, mas **sem depender de serviços externos pagos**. Por isso, usaremos um modelo pequeno e offline, apenas para fins de avaliação da implementação e não da qualidade das respostas.

O sistema deverá receber uma descrição textual de um incidente e retornar, em **JSON válido**, os seguintes campos:

- `data_ocorrencia` – data e hora do incidente (se presente no texto)
- `local` – local do incidente
- `tipo_incidente` – tipo ou categoria do incidente
- `impacto` – descrição breve do impacto gerado

#### Exemplo de entrada

```text
Ontem às 14h, no escritório de São Paulo, houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas.
```

#### Exemplo de saída esperada

```json
{
  "data_ocorrencia": "2025-08-12 14:00",
  "local": "São Paulo",
  "tipo_incidente": "Falha no servidor",
  "impacto": "Sistema de faturamento indisponível por 2 horas"
}
```

O foco da avaliação **não será a precisão do modelo**, mas sim as boas práticas de desenvolvimento, a organização do código e a capacidade de integração com um LLM local.

---

## Atividades

Para os fins deste exercício, você deve desenvolver as seguintes atividades:

- Criar uma API em Python que:

  - Receba como entrada um texto de incidente (via parâmetro na requisição)
  - Utilize um LLM local para extrair as informações solicitadas
  - Retorne a saída estruturada no formato JSON

- Implementar um pipeline simples de pré-processamento para melhorar a consistência do texto antes do envio ao modelo

- Garantir que a API seja facilmente reproduzível e possa rodar localmente sem dependências externas de nuvem

---

## Entregáveis

- Código Python da API
- Instruções claras de execução em um README
- Código versionado em um repositório Git

---

## Instruções para uso de LLM offline (Opcional)

Para este teste, você pode utilizar qualquer LLM. Porém, caso não queira gastar seus tokens, poderá utilizar o **Ollama** com um modelo local pequeno. A qualidade das respostas não será avaliada, pois o objetivo é apenas validar a integração e boas práticas.

#### Passos para instalação no Linux/WSL:

```bash
# 1. Instalar o Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Iniciar o serviço Ollama
ollama serve &

# 3. Baixar um modelo pequeno para testes (ex.: TinyLlama ou Llama 3.2)
ollama pull tinyllama
```

Sua API deve se comunicar com o **Ollama local** para processar o texto de entrada e retornar o JSON de saída.

---

## Critérios de avaliação

- Boas práticas de desenvolvimento
- Reprodutibilidade de ambiente
- Clareza das instruções
- Organização e legibilidade do código
