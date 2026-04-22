# Dashboard Comercial — Grifos Distribuidora

App Streamlit para acompanhamento diário de metas, positivação BPC e estoque.

## Como rodar

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Rodar o app
streamlit run app.py
```

O browser abre automaticamente em http://localhost:8501

## Fluxo de atualização diária

| Passo | Rotina Winthor | Arquivo | Upload no app |
|-------|---------------|---------|--------------|
| 1 | 8025 — Mapa de Vendas | CSV | ✅ Obrigatório |
| 2 | 1464 — BPC com ST (Fornec. 19) | XLSX | ✅ Recomendado |
| 3 | 1464 — BPC sem ST (Fornec. 19) | XLSX | ✅ Recomendado |
| 4 | 8066 — Estoque Valorizado | CSV | Opcional |
| 5 | 105 — Posição de Estoque | XLS | Opcional |
| 6 | 1464 — Todos BUs (Compliance) | XLSX | Opcional |

## Deploy gratuito (Streamlit Community Cloud)

1. Suba esta pasta para um repositório GitHub (privado ou público)
2. Acesse https://share.streamlit.io
3. Conecte o repositório e aponte para `app.py`
4. Compartilhe o link com seu gerente — ele abre no celular também
