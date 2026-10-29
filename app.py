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


# Conexão com o Google Sheets usando Secrets
@st.cache_resource
def conectar_gsheets():
  scope = [
      "https://spreadsheets.google.com/feeds",
      "https://www.googleapis.com/auth/drive",
  ]
  creds_dict = dict(st.secrets["gcp_service_account"])
  creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
  client = gspread.authorize(creds)
  # Substitua pelo nome exato da sua planilha
  sheet = client.open("ControleComercial")
  return sheet


try:
  sh = conectar_gsheets()
  sheet_lancamentos = sh.worksheet("Lancamentos")
  sheet_baixas = sh.worksheet("Baixas")
  sheet_params = sh.worksheet("Parametros")
except Exception as e:
  st.error(
      f"Erro ao conectar com o Google Sheets. Verifique suas secrets. Erro: {e}"
  )
  st.stop()


# Carregar parâmetros (Listas suspensas)
@st.cache_data(ttl=60)
def carregar_parametros():
  data = sheet_params.get_all_records()
  df = pd.DataFrame(data)
  gerentes = df["Gerentes"].dropna().tolist()
  tipos = df["Tipos_Compromisso"].dropna().tolist()
  formas = df["Formas_Pagamento"].dropna().tolist()
  return gerentes, tipos, formas


gerentes_list, tipos_list, formas_list = carregar_parametros()

# Cabeçalho Principal
st.title("📊 Painel Gerencial • Controle de Pagamentos Comerciais")
st.markdown("---")

# Abas do Aplicativo
aba1, aba2, aba3 = st.tabs(
    ["🚀 Novo Lançamento", "📥 Registrar Baixa (Pagamento)", "📈 Dashboard"]
)

# ==========================================
# ABA 1: LANÇAMENTO (Baseado no Print 1)
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
      cnpj = st.text_input(
          "CNPJ", placeholder="00.000.000/0000-00", max_chars=18
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
        # Gerar ID único para o lançamento (ex: LAN-00001)
        existing_data = sheet_lancamentos.get_all_records()
        next_id = f"LAN-{len(existing_data) + 1:05d}"

        row = [
            next_id,
            str(data_lancamento),
            gerente_resp,
            codigo_pdv,
            cnpj,
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
        st.success(f"Lançamento {next_id} salvo com sucesso!")

# ==========================================
# ABA 2: BAIXA (Baseado no Print 2)
# ==========================================
with aba2:
  st.subheader("Registrar pagamento")

  # Buscar lançamentos existentes para escolha
  df_lanc = pd.DataFrame(sheet_lancamentos.get_all_records())

  with st.form("form_baixa", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
      id_opcoes = (
          df_lanc["id_lancamento"].tolist() if not df_lanc.empty else []
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

        # Atualizar status na aba de lançamentos (Lógica simples de exemplo)
        # Você pode aprimorar somando os pagamentos daquele ID na aba Baixas
        cell = sheet_lancamentos.find(id_lancamento)
        if cell:
          # Atualiza a coluna de status (assumindo que seja a última coluna, índice 13)
          sheet_lancamentos.update_cell(cell.row, 13, "Pago / Parcial")

        st.success(f"Pagamento registrado para o lançamento {id_lancamento}!")

# ==========================================
# ABA 3: DASHBOARD (Baseado no Print 4)
# ==========================================
with aba3:
  st.subheader("Painel de Indicadores")

  if df_lanc.empty:
    st.info("Ainda não há dados cadastrados na planilha.")
  else:
    # Métricas Principais topo
    total_debitos = (
        df_lanc["valor_debito"].astype(float).sum()
        if "valor_debito" in df_lanc.columns
        else 0
    )

    # Carregar baixas para calcular total pago
    df_baixas = pd.DataFrame(sheet_baixas.get_all_records())
    total_pago = (
        df_baixas["valor_pago"].astype(float).sum()
        if not df_baixas.empty and "valor_pago" in df_baixas.columns
        else 0
    )
    saldo_aberto = total_debitos - total_pago

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("TOTAL DE DÉBITOS CADASTRADOS", f"R$ {total_debitos:,.2f}")
    col_m2.metric("TOTAL PAGO", f"R$ {total_pago:,.2f}")
    col_m3.metric("SALDO TOTAL EM ABERTO", f"R$ {saldo_aberto:,.2f}")

    st.markdown("---")

    # Gráficos e Tabelas Resumo
    col_g1, col_g2 = st.columns(2)

    with col_g1:
      st.markdown("### Por Tipo de Compromisso")
      if "tipo_compromisso" in df_lanc.columns:
        resumo_tipo = (
            df_lanc.groupby("tipo_compromisso")["valor_debito"]
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
      if "gerente" in df_lanc.columns:
        resumo_gerente = (
            df_lanc.groupby("gerente")["valor_debito"].sum().reset_index()
        )
        fig_gerente = px.pie(
            resumo_gerente,
            names="gerente",
            values="valor_debito",
            title="Participação por Gerente",
        )
        st.plotly_chart(fig_gerente, use_container_width=True)

    st.markdown("### Base Completa de Lançamentos")
    st.dataframe(df_lanc, use_container_width=True)
