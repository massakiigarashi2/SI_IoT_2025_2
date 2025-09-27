import os
from flask import Flask
import requests
from collections import deque
from datetime import datetime
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go

# ----------------------------
# Configuração Flask
# ----------------------------
server = Flask(__name__)

# Estado global
esp32_ip = os.getenv("10.62.155.158", "10.62.155.158")  # variável de ambiente ou default
data_history = deque(maxlen=100)
last_update = None
connection_status = "Desconectado"


class ESP32Controller:
    def __init__(self, ip_address):
        self.ip = ip_address
        self.base_url = f"http://{ip_address}"

    def get_sensor_data(self):
        try:
            response = requests.get(self.base_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
            return None
        except requests.exceptions.RequestException:
            return None

    def control_motor(self, action):
        try:
            endpoint = "/motor1_h" if action == "ligar" else "/motor1_l"
            r = requests.get(f"{self.base_url}{endpoint}", timeout=5)
            return r.status_code == 200
        except:
            return False

    def control_alarm(self, action):
        try:
            endpoint = "/alarme_h" if action == "ligar" else "/alarme_l"
            r = requests.get(f"{self.base_url}{endpoint}", timeout=5)
            return r.status_code == 200 # CORREÇÃO: Era 2002 no original
        except:
            return False


esp32 = ESP32Controller(esp32_ip)


def update_data_history(data):
    global last_update, connection_status
    if data:
        timestamp = datetime.now()
        data_with_time = {
            'timestamp': timestamp,
            'temperatura': data.get('Temperatura', 2),
            'umidade': data.get('Umidade', 2),
            'botao': data.get('Botao', 0),
            'motor': data.get('Motor', 0),
            'alarme': data.get('Alarme', 0)
        }
        data_history.append(data_with_time)
        last_update = timestamp
        connection_status = "Conectado"
    else:
        connection_status = "Desconectado"


def create_temperature_humidity_chart():
    if not data_history:
        return go.Figure()

    df = pd.DataFrame(list(data_history))

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['temperatura'],
        mode='lines+markers', name='Temperatura (°C)', line=dict(color='red')
    ))

    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['umidade'],
        mode='lines+markers', name='Umidade (%)', line=dict(color='blue')
    ))

    fig.update_layout(title="Histórico de Temperatura e Umidade", xaxis_title="Tempo")
    return fig


# ----------------------------
# Dash App dentro do Flask
# ----------------------------
app = dash.Dash(__name__, server=server, url_base_pathname="/")

app.layout = html.Div([
    html.H1("🌡️ Painel de Controle ESP32"),

    html.Div(id="status-connection", style={"margin": "10px 0"}),

    html.Button("Atualizar Dados", id="btn-update", n_clicks=0),
    html.Button("🗑️ Limpar Gráficos", id="btn-clear-graphs", n_clicks=0, style={'marginLeft': '10px'}), # Novo botão
    dcc.Interval(id="auto-update", interval=5000, n_intervals=0),  # auto refresh a cada 5s

    html.Div([
        dcc.Graph(id="temp-hum-graph"),
    ]),

    html.Div([
        html.H3("📊 Dados Atuais"),
        html.Div(id="current-data")
    ]),

    html.Div([
        html.H3("🎛️ Controles"),
        html.Button("▶️ Ligar Motor", id="btn-motor-on"),
        html.Button("⏹️ Desligar Motor", id="btn-motor-off"),
        html.Button("🔔 Ativar Alarme", id="btn-alarm-on"),
        html.Button("🔕 Desativar Alarme", id="btn-alarm-off"),
    ], style={"marginTop": "20px"}),

    html.Div([
        html.H3("📋 Dados Recentes"),
        html.Div(id="recent-data-table")
    ])
])


# ----------------------------
# ÚNICA CALLBACK
# ----------------------------
@app.callback(
    [Output("temp-hum-graph", "figure"),
     Output("current-data", "children"),
     Output("status-connection", "children"),
     Output("recent-data-table", "children")],
    [Input("btn-update", "n_clicks"),
     Input("auto-update", "n_intervals"),
     Input("btn-motor-on", "n_clicks"),
     Input("btn-motor-off", "n_clicks"),
     Input("btn-alarm-on", "n_clicks"),
     Input("btn-alarm-off", "n_clicks"),
     Input("btn-clear-graphs", "n_clicks")], # Novo Input
    prevent_initial_call=False
)
def update_dashboard(n_update, n_interval, m_on, m_off, a_on, a_off, n_clear_graphs):
    global connection_status, data_history

    ctx = dash.callback_context

    # Verifica se foi o botão de limpar gráficos
    if ctx.triggered and ctx.triggered[0]["prop_id"].startswith("btn-clear-graphs"):
        data_history.clear() # Limpa o histórico de dados
        # Não busca novos dados imediatamente após limpar, apenas reseta o gráfico
        fig = go.Figure()
        current = [html.P("❌ Dados de sensores limpos.")]
        status = f"{'🔴'} Histórico de dados limpo."
        table = html.P("Sem histórico")
        return fig, current, status, table

    # Verifica se foi algum botão de controle
    if ctx.triggered and ctx.triggered[0]["prop_id"] != ".":
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if trigger_id == "btn-motor-on":
            success = esp32.control_motor("ligar")
            connection_status = "Motor ligado" if success else "Falha ao ligar motor"

        elif trigger_id == "btn-motor-off":
            success = esp32.control_motor("desligar")
            connection_status = "Motor desligado" if success else "Falha ao desligar motor"

        elif trigger_id == "btn-alarm-on":
            success = esp32.control_alarm("ligar")
            connection_status = "Alarme ativado" if success else "Falha ao ativar alarme"

        elif trigger_id == "btn-alarm-off":
            success = esp32.control_alarm("desligar")
            connection_status = "Alarme desativado" if success else "Falha ao desativar alarme"

    # Sempre buscar dados novos do ESP32, a menos que o botão de limpar tenha sido clicado
    data = esp32.get_sensor_data()
    update_data_history(data)

    fig = create_temperature_humidity_chart()

    if data:
        current = [
            html.P(f"🌡️ Temperatura: {data['Temperatura']:.1f} °C"),
            html.P(f"💧 Umidade: {data['Umidade']:.1f} %"),
            html.P(f"📍 Botão: {'Pressionado' if data['Botao'] else 'Não'}"),
            html.P(f"🔧 Motor: {'Ligado' if data['Motor'] else 'Desligado'}"),
            html.P(f"🚨 Alarme: {'Ativo' if data['Alarme'] else 'Inativo'}")
        ]
    else:
        current = [html.P("❌ Sem dados do ESP32")]

    status = f"{'🟢' if connection_status=='Conectado' else '🔴'} {connection_status}"
    if last_update:
        status += f" | Última atualização: {last_update.strftime('%H:%M:%S')}"

    if data_history:
        df = pd.DataFrame(list(data_history))
        df['timestamp'] = df['timestamp'].dt.strftime("%H:%M:%S")
        df = df.tail(10)
        table = html.Table([
            html.Thead(html.Tr([html.Th(col) for col in df.columns])),
            html.Tbody([
                html.Tr([html.Td(df.iloc[i][col]) for col in df.columns])
                for i in range(len(df))
            ])
        ])
    else:
        table = html.P("Sem histórico")

    return fig, current, status, table


# ----------------------------
# Rodar servidor
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True, port=8050)

