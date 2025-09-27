import os
from flask import Flask
import requests
from collections import deque
from datetime import datetime
import pandas as pd
import dash
from dash import dcc, html, Input, Output, ctx
import plotly.graph_objects as go

# ----------------------------
# Configuração
# ----------------------------
server = Flask(__name__)
esp32_ip = os.getenv("ESP32_IP", "10.62.155.158")
data_history = deque(maxlen=100)
last_update = None
connection_status = "Desconectado"

# --- NOVO: URL do Google Form ---
GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSf0DGncBYg6IJwhoB0PEX4PIh1XsZj1OUcVpGKHGoSgDNgN1w/formResponse"

# ----------------------------
# Funções de Comunicação
# ----------------------------
class ESP32Controller:
    """Classe para encapsular a comunicação com o ESP32."""
    def __init__(self, ip_address ):
        self.ip = ip_address
        self.base_url = f"http://{ip_address}"

    def get_sensor_data(self ):
        """Busca dados dos sensores do ESP32."""
        try:
            response = requests.get(self.base_url, timeout=5)
            response.raise_for_status()
            if "application/json" in response.headers.get("Content-Type", ""):
                data = response.json()
                return data[0] if isinstance(data, list) and data else None
            return None
        except requests.exceptions.RequestException:
            return None

    def control_motor(self, action: str):
        endpoint = "/motor1_h" if action == "ligar" else "/motor1_l"
        return self._send_command(endpoint)

    def control_alarm(self, action: str):
        endpoint = "/alarme_h" if action == "ligar" else "/alarme_l"
        return self._send_command(endpoint)

    def _send_command(self, endpoint: str):
        try:
            r = requests.get(f"{self.base_url}{endpoint}", timeout=3)
            return r.status_code == 200
        except requests.exceptions.RequestException:
            return False

def send_data_to_google_form(data: dict):
    """
    NOVO: Envia os dados dos sensores para um Google Form via requisição GET.
    """
    if not data:
        return False
    
    try:
        # Mapeia os dados para os 'entry' IDs do formulário
        params = {
            'entry.1518093638': data.get('Temperatura'),
            'entry.1621899341': data.get('Umidade'),
            'entry.1262249026': data.get('Botao'),
            'entry.1332691306': data.get('Alarme'),
            'submit': 'Submit' # Parâmetro padrão de submissão
        }
        
        response = requests.get(GOOGLE_FORM_URL, params=params, timeout=3)
        # O Google Forms retorna 200 mesmo em caso de erro de entrada, 
        # então apenas checar o status da requisição é suficiente.
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

esp32 = ESP32Controller(esp32_ip)

# (O resto das funções auxiliares como create_temperature_humidity_chart e update_data_history permanecem as mesmas)
def update_data_history(data):
    global last_update, connection_status
    if data:
        timestamp = datetime.now()
        data_with_time = {
            'timestamp': timestamp,
            'temperatura': data.get('Temperatura'),
            'umidade': data.get('Umidade'),
            'botao': data.get('Botao', 0),
            'motor': data.get('Motor', 0),
            'alarme': data.get('Alarme', 0)
        }
        data_history.append(data_with_time)
        last_update = timestamp
        connection_status = "Conectado"
    else:
        connection_status = "Falha na conexão"

def create_temperature_humidity_chart():
    if not data_history: return go.Figure()
    df = pd.DataFrame(list(data_history)).dropna(subset=['temperatura', 'umidade'])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['temperatura'], mode='lines+markers', name='Temperatura (°C)', line=dict(color='red')))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['umidade'], mode='lines+markers', name='Umidade (%)', line=dict(color='blue'), yaxis="y2"))
    fig.update_layout(title="Histórico de Temperatura e Umidade", xaxis_title="Tempo", yaxis=dict(title='Temperatura (°C)'), yaxis2=dict(title='Umidade (%)', overlaying='y', side='right'), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

# ----------------------------
# Layout do Dash App
# ----------------------------
app = dash.Dash(__name__, server=server, url_base_pathname="/")
app.layout = html.Div([
    html.H1("🌡️ Painel de Controle ESP32 com Integração Google Forms"),
    dcc.Loading(id="loading-icon", type="default", children=[
        html.Div(id="status-connection", style={"margin": "10px 0"}),
        html.Div(id="current-data"),
    ]),
    html.Button("Atualizar Dados", id="btn-update", n_clicks=0),
    html.Button("🗑️ Limpar Gráficos", id="btn-clear-graphs", n_clicks=0, style={'marginLeft': '10px'}),
    dcc.Interval(id="auto-update", interval=5000, n_intervals=0),
    dcc.Graph(id="temp-hum-graph"),
    html.Div([
        html.H3("🎛️ Controles"),
        html.Button("▶️ Ligar Motor", id="btn-motor-on", n_clicks=0),
        html.Button("⏹️ Desligar Motor", id="btn-motor-off", n_clicks=0),
        html.Button("🔔 Ativar Alarme", id="btn-alarm-on", n_clicks=0),
        html.Button("🔕 Desativar Alarme", id="btn-alarm-off", n_clicks=0),
    ], style={"marginTop": "20px"}),
    html.Div([
        html.H3("📋 Dados Recentes (últimos 10)"),
        html.Div(id="recent-data-table")
    ])
])

# ----------------------------
# Callback Principal
# ----------------------------
@app.callback(
    Output("temp-hum-graph", "figure"),
    Output("current-data", "children"),
    Output("status-connection", "children"),
    Output("recent-data-table", "children"),
    Input("btn-update", "n_clicks"),
    Input("auto-update", "n_intervals"),
    Input("btn-motor-on", "n_clicks"),
    Input("btn-motor-off", "n_clicks"),
    Input("btn-alarm-on", "n_clicks"),
    Input("btn-alarm-off", "n_clicks"),
    Input("btn-clear-graphs", "n_clicks"),
    prevent_initial_call=False
)
def update_dashboard(n_update, n_interval, m_on, m_off, a_on, a_off, n_clear):
    global connection_status, data_history
    
    triggered_id = ctx.triggered_id if ctx.triggered_id else 'auto-update'

    if triggered_id == "btn-clear-graphs":
        data_history.clear()
        return create_temperature_humidity_chart(), html.P("Histórico limpo."), "⚪ Histórico limpo.", html.P("Sem dados.")

    # Lógica de controle de botões
    if triggered_id.startswith("btn-"):
        if triggered_id == "btn-motor-on":
            connection_status = "Motor ligado" if esp32.control_motor("ligar") else "Falha ao ligar motor"
        elif triggered_id == "btn-motor-off":
            connection_status = "Motor desligado" if esp32.control_motor("desligar") else "Falha ao desligar motor"
        elif triggered_id == "btn-alarm-on":
            connection_status = "Alarme ativado" if esp32.control_alarm("ligar") else "Falha ao ativar alarme"
        elif triggered_id == "btn-alarm-off":
            connection_status = "Alarme desativado" if esp32.control_alarm("desligar") else "Falha ao desativar alarme"

    # Busca de dados do ESP32
    data = esp32.get_sensor_data()
    update_data_history(data)

    # --- NOVO: Envio para o Google Form ---
    if data:
        google_success = send_data_to_google_form(data)
        if google_success:
            # Atualiza o status para refletir o envio bem-sucedido
            connection_status = "Conectado e Dados Enviados"
        else:
            connection_status = "Falha ao enviar para o Google"

    # Geração dos componentes de saída
    fig = create_temperature_humidity_chart()
    
    if data_history:
        last_data = data_history[-1]
        current = [
            html.P(f"🌡️ Temperatura: {last_data['temperatura']:.1f} °C" if last_data.get('temperatura') is not None else "Temperatura: N/A"),
            html.P(f"💧 Umidade: {last_data['umidade']:.1f} %" if last_data.get('umidade') is not None else "Umidade: N/A"),
            html.P(f"🔘 Botão: {'Pressionado' if last_data['botao'] else 'Solto'}"),
            html.P(f"⚙️ Motor: {'Ligado' if last_data['motor'] else 'Desligado'}"),
            html.P(f"🚨 Alarme: {'Ativo' if last_data['alarme'] else 'Inativo'}")
        ]
        df = pd.DataFrame(list(data_history)); df['timestamp'] = df['timestamp'].dt.strftime("%H:%M:%S"); df = df.tail(10).iloc[::-1]
        table = html.Table([html.Thead(html.Tr([html.Th(col) for col in df.columns])), html.Tbody([html.Tr([html.Td(df.iloc[i][col]) for col in df.columns]) for i in range(len(df))])], style={'width': '100%', 'textAlign': 'center'})
    else:
        current = [html.P("❌ Sem dados do ESP32")]
        table = html.P("Sem histórico de dados.")

    status_icon = '🟢' if "Conectado" in connection_status else '🟡' if "Google" in connection_status else '🔴'
    status_msg = f"{status_icon} {connection_status}"
    if last_update:
        status_msg += f" | Última atualização: {last_update.strftime('%H:%M:%S')}"

    return fig, current, status_msg, table

# ----------------------------
# Rodar servidor
# ----------------------------
if __name__ == "__main__":
    app.run(debug=False, port=8050)
