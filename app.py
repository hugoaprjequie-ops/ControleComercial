from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px
import streamlit as st

# Configuração da Página
st.set_page_config(
    page_title="Controle de Pagamentos Comerciais", page_icon="💰", layout="wide"
)


# Conexão com o Google Sheets
def conectar_gsheets():
  scope = [
      "https://spreadsheets.google.com/feeds",
      "https://www.googleapis.com/auth/drive",
  ]
  creds_dict = dict(st.secrets["gcp_service_account"])

  if "private_key" in creds_dict:
    key = creds_dict["private_key"]
    key = key.replace("\\n", "\n")
    creds_dict["private_key"] = key

  creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
  client = gspread.authorize(creds)
  sheet = client.open("ControleComercial")
  return sheet


try:
  sh = conectar_gsheets()
  sheet_lancamentos = sh.worksheet("Lancamentos")
  sheet_baixas = sh.worksheet("Baixas")
  sheet_params = sh.worksheet("Parametros")
  st.sidebar.success("✅ Conectado ao Google Sheets!")
except Exception as e:
  st.error(
      f"Erro ao conectar com o Google Sheets. Verifique suas secrets. Erro: {e}"
  )
  st.stop()

# Botão na Barra Lateral para Atualizar os Dados manualmente
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Atualizar Dados do Sheets"):
  st.cache_data.clear()
  st.rerun()


# Carregar parâmetros atualizados da planilha
def carregar_parametros():
  try:
    data = sheet_params.get_all_records()
    df = pd.DataFrame(data)
    gerentes = (
        df["Gerentes"].dropna().unique().tolist()
        if "Gerentes" in df.columns
        else []
    )
    tipos = (
        df["Tipos_Compromisso"].dropna().unique().tolist()
        if "Tipos_Compromisso" in df.columns
        else []
    )
    formas = (
        df["Formas_Pagamento"].dropna().unique().tolist()
        if "Formas_Pagamento" in df.columns
        else []
    )
    return gerentes, tipos, formas
  except Exception:
    return (
        ["ADRIANO", "MATHEUS", "JULIANO"],
        ["Contrato", "Ação de Mercado", "BL (Bateu Levou)"],
        ["Pix", "TED/DOC", "Boleto", "Depósito"],
    )


gerentes_list, tipos_list, formas_list = carregar_parametros()

# Cabeçalho Principal
st.title("📊 Painel Gerencial • Controle de Pagamentos Comerciais")
st.markdown("---")

# Abas do Aplicativo
aba1, aba2, aba3 = st.tabs(
    ["🚀 Novo Lançamento", "📥 Registrar Baixa (Pagamento)", "📈 Dashboard"]
)

# ==========================================
# ABA 1: LANÇAMENTO
# ==========================================
with aba1:
  st.subheader("Novo lançamento (débito)")

  with st.form("form_lancamento", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
      data_lancamento = st.date_input(
          "Data do lançamento *", value=datetime.today()
      )
      gerente_resp = st.selectbox(
          "Gerente responsável *", ["Selecione..."] + gerentes_list
      )
      codigo_pdv = st.text_input("Código do cliente (PDV) *")
      nome_cliente = st.text_input("Nome do cliente *")
      tipo_comp = st.selectbox(
          "Tipo de compromisso *", ["Selecione..."] + tipos_list
      )
      descricao = st.text_input("Descrição do compromisso *")

    with col2:
      cnpj_cpf = st.text_input(
          "CNPJ/CPF", placeholder="000.000.000-00 / 00.000.000/0000-00", max_chars=18
      )
      contrato_campanha = st.text_input("Nº contrato / campanha")
      data_vencimento = st.date_input("Data de vencimento *")
      valor_debito = st.number_input(
          "Valor total do débito (R$) *", min_value=0.0, format="%.2f"
      )
      observacoes = st.text_area("Observações")

    submitted = st.form_submit_button("Salvar lançamento")

    if submitted:
      if (
          gerente_resp == "Selecione..."
          or tipo_comp == "Selecione..."
          or not codigo_pdv
          or not nome_cliente
          or not descricao
      ):
        st.error(
            "Por favor, preencha todos os campos obrigatórios marcados com *."
        )
      else:
        existing_data = sheet_lancamentos.get_all_records()
        next_id = f"LAN-{len(existing_data) + 1:05d}"

        row = [
            next_id,
            str(data_lancamento),
            gerente_resp,
            codigo_pdv,
            cnpj_cpf,  # Atualizado para CNPJ/CPF
            nome_cliente,
            tipo_comp,
            contrato_campanha,
            descricao,
            str(data_vencimento),
            float(valor_debito),
            observacoes,
            "Pendente",
        ]
        sheet_lancamentos.append_row(row)
        st.success(f"Lançamento {next_id} salvo e integrado com o Sheets!")
        st.rerun()

# ==========================================
# ABA 2: BAIXA (Pagamento)
# ==========================================
with aba2:
  st.subheader("Registrar pagamento")

  try:
    df_lanc = pd.DataFrame(sheet_lancamentos.get_all_records())
  except Exception:
    df_lanc = pd.DataFrame()

  with st.form("form_baixa", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
      id_opcoes = (
          df_lanc["id_lancamento"].tolist()
          if not df_lanc.empty and "id_lancamento" in df_lanc.columns
          else []
      )
      id_lancamento = st.selectbox(
          "ID do lançamento *", options=["Selecione..."] + id_opcoes
      )
      data_pagamento = st.date_input(
          "Data do pagamento *", value=datetime.today()
      )
      forma_pag = st.selectbox(
          "Forma de pagamento", ["Selecione..."] + formas_list
      )

    with col2:
      valor_pago = st.number_input(
          "Valor pago (R$) *", min_value=0.0, format="%.2f"
      )
      comprovante_link = st.text_input(
          "Comprovante (link)", placeholder="https://..."
      )
      obs_baixa = st.text_area("Observações da baixa")

    submitted_baixa = st.form_submit_button("Registrar pagamento")

    if submitted_baixa:
      if id_lancamento == "Selecione..." or valor_pago <= 0:
        st.error(
            "Selecione um ID de lançamento válido e informe um valor pago"
            " maior que zero."
        )
      else:
        row_baixa = [
            id_lancamento,
            str(data_pagamento),
            float(valor_pago),
            forma_pag if forma_pag != "Selecione..." else "",
            comprovante_link,
            obs_baixa,
        ]
        sheet_baixas.append_row(row_baixa)

        cell = sheet_lancamentos.find(id_lancamento)
        if cell:
          sheet_lancamentos.update_cell(cell.row, 13, "Pago / Parcial")

        st.success(f"Pagamento registrado para o lançamento {id_lancamento}!")
        st.rerun()

# ==========================================
# ABA 3: DASHBOARD COM FILTROS AVANÇADOS
# ==========================================
with aba3:
  st.subheader("Painel de Indicadores e Filtros")

  if df_lanc.empty or "valor_debito" not in df_lanc.columns:
    st.info("Ainda não há dados cadastrados na planilha.")
  else:
    st.markdown("### 🔍 Filtros do Dashboard")
    f_col1, f_col2, f_col3 = st.columns(3)

    with f_col1:
      gerentes_disponiveis = (
          ["Todos"] + df_lanc["gerente"].dropna().unique().tolist()
          if "gerente" in df_lanc.columns
          else ["Todos"]
      )
      filtro_gerente = st.selectbox("Filtrar por Gerente", gerentes_disponiveis)

    with f_col2:
      tipos_disponiveis = (
          ["Todos"] + df_lanc["tipo_compromisso"].dropna().unique().tolist()
          if "tipo_compromisso" in df_lanc.columns
          else ["Todos"]
      )
      filtro_tipo = st.selectbox(
          "Filtrar por Tipo de Compromisso", tipos_disponiveis
      )

    with f_col3:
      clientes_disponiveis = (
          ["Todos"] + df_lanc["nome_cliente"].dropna().unique().tolist()
          if "nome_cliente" in df_lanc.columns
          else ["Todos"]
      )
      filtro_cliente = st.selectbox(
          "Filtrar por Nome do Cliente", clientes_disponiveis
      )

    # Aplicando os filtros no DataFrame
    df_filtrado = df_lanc.copy()
    if filtro_gerente != "Todos":
      df_filtrado = df_filtrado[df_filtrado["gerente"] == filtro_gerente]
    if filtro_tipo != "Todos":
      df_filtrado = df_filtrado[
          df_filtrado["tipo_compromisso"] == filtro_tipo
      ]
    if filtro_cliente != "Todos":
      df_filtrado = df_filtrado[df_filtrado["nome_cliente"] == filtro_cliente]

    st.markdown("---")

    total_debitos = (
        df_filtrado["valor_debito"].astype(float).sum()
        if not df_filtrado.empty
        else 0
    )

    try:
      df_baixas = pd.DataFrame(sheet_baixas.get_all_records())
      if not df_baixas.empty and "id_lancamento" in df_baixas.columns:
        ids_filtrados = df_filtrado["id_lancamento"].tolist()
        df_baixas_filtradas = df_baixas[
            df_baixas["id_lancamento"].isin(ids_filtrados)
        ]
        total_pago = df_baixas_filtradas["valor_pago"].astype(float).sum()
      else:
        total_pago = 0.0
    except Exception:
      total_pago = 0.0

    saldo_aberto = total_debitos - total_pago

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric(
        "TOTAL DE DÉBITOS (FILTRADO)",
        f"R$ {total_debitos:,.2f}",
        delta=f"{len(df_filtrado)} registros",
    )
    col_m2.metric("TOTAL PAGO (FILTRADO)", f"R$ {total_pago:,.2f}")
    col_m3.metric("SALDO TOTAL EM ABERTO", f"R$ {saldo_aberto:,.2f}")

    st.markdown("---")

    col_g1, col_g2 = st.columns(2)

    with col_g1:
      st.markdown("### Por Tipo de Compromisso")
      if not df_filtrado.empty and "tipo_compromisso" in df_filtrado.columns:
        resumo_tipo = (
            df_filtrado.groupby("tipo_compromisso")["valor_debito"]
            .sum()
            .reset_index()
        )
        fig_tipo = px.bar(
            resumo_tipo,
            x="tipo_compromisso",
            y="valor_debito",
            title="Débitos por Tipo de Compromisso",
        )
        st.plotly_chart(fig_tipo, use_container_width=True)

    with col_g2:
      st.markdown("### Distribuição por Gerente")
      if not df_filtrado.empty and "gerente" in df_filtrado.columns:
        resumo_gerente = (
            df_filtrado.groupby("gerente")["valor_debito"].sum().reset_index()
        )
        fig_gerente = px.pie(
            resumo_gerente,
            names="gerente",
            values="valor_debito",
            title="Participação por Gerente",
        )
        st.plotly_chart(fig_gerente, use_container_width=True)

    st.markdown("### Base de Lançamentos Filtrados")
    st.dataframe(df_filtrado, use_container_width=True)
