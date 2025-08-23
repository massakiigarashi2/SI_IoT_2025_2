/*******************************************************************************
          Algoritmo de envio de e-mail com texto simples com ESP32
                            Sketch Principal
                      Criado em 23 de agosto de 2025
                          por Massaki Igarashi
  Curso: Soluções Integradas com IoT | SENAI Roberto Mange | Campinas - SP
*******************************************************************************/
// Inclusão da(s) biblioteca(s)
#include <WiFi.h> // Biblioteca nativa do ESP32
#include <ESP_Mail_Client.h>  // Biblioteca de cliente de e-mail do 
//                                Arduino para enviar.
//                                Referência: https://github.com/mobizt/ESP-Mail-Client
// Configurações da rede WiFi à se conectar
#define WIFI_SSID "MSK2"
#define WIFI_PASSWORD "msk54321"
// Configurações do SMTP host
#define SMTP_HOST "smtp.gmail.com" // SMTP host
#define SMTP_PORT 465 // SMTP port
// As credenciais de login
#define AUTOR_EMAIL "igarashimassaki@gmail.com"
#define AUTOR_SENHA "xxxxxxxxxxxxxxxx" //Aqui você cola a senha gerada pelo Google na opções de Segurança / Senhas de App
// O objeto de sessão SMTP usado para envio de e-mail
SMTPSession smtp;
// Protótipos das Funções
void smtpCallback(SMTP_Status status);
bool enviaEmail_TXT(String nomeRemetente,
                    String emailRemetente,
                    String senhaRemetente,
                    String assunto,
                    String nomeDestinatario,
                    String emailDestinatario,
                    String messageTXT,
                    String stmpHost,
                    int stmpPort);
float S=0; //variavel para SOMATORIO DAS leituras (Entrada 36, A0)
const int Namostras = 25; //NUmero de amostras para ajuste de media movel da leitura analogica Pinos 36 e 39
void setup() {
  // Inicia Serial
  Serial.begin(115200);
  Serial.println();
  delay(1000);
  // Inicia conexão WiFi
  Serial.println("Conectando à rede WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) // Enquanto o status de conexão ao WiFi
    //                                      não for bem sucedido, ...
  {
    Serial.print(".");
    delay(200);
  }
  // Mostra na Serial que a conexão está realizada e mostra o IP do ESP32 na rede
  Serial.println("\nWiFi conectado.");

  // Habilita a depuração via porta serial:
  //    0: nenhuma depuração
  //    1: depuração básica
  smtp.debug(0);

  // Define a função de retorno de chamada para obter os resultados de envio
  smtp.callback(smtpCallback);

  //Define a mensagem de texto a ser enviada
  String messageTXT = "Hello Massaki! Teste de envio de E-mail ESP32.";
  // função que envia o e-mail
  enviaEmail_TXT("Prof. Massaki Igarashi",
                 AUTOR_EMAIL,
                 AUTOR_SENHA,
                 "Teste de E-mail ESP32",
                 "Para: Massaki",
                 "prof.massaki@gmail.com",
                 messageTXT,
                 SMTP_HOST,
                 SMTP_PORT);
  while (1); // loop infinito
}
void loop() {
  for(int i=0; i<Namostras; i++){
    float LeituraANALOGICA = analogRead(36)*3.3/1023.0;
    S+=LeituraANALOGICA;
  }
  float Tensao = S/Namostras;
  Serial.print("Tesão = ");
  Serial.print(Tensao);
  Serial.println(" Volts");
  delay(500);
}
/**
  Envia um e-mail para um destinatário.
  @param nomeRemetente - o nome ao qual será mostrado do remetente
  @param emailRemetente - o email do remetente
  @param senhaRemetente - a senha criada em Senhas de app
  @param assunto - o assunto do e-mail
  @param nomeDestinatario - o nome do destinatário
  @param emailDestinatario - o email do destinatário
  @param messageTXT - a mensagem de texto do e-mail
  @param stmpHost - o servidor SMTP
  @param stmpPort - a porta SSL do servidor SMTP

  @return - true se envio foi bem sucedido ou false se houve alguma falha
*/
bool enviaEmail_TXT(String nomeRemetente,
                    String emailRemetente,
                    String senhaRemetente,
                    String assunto,
                    String nomeDestinatario,
                    String emailDestinatario,
                    String messageTXT,
                    String stmpHost,
                    int stmpPort) {
                      
  // Objeto para declarar os dados de configuração da sessão
  ESP_Mail_Session session;
  // Defina os dados de configuração da sessão
  session.server.host_name = stmpHost;
  session.server.port = stmpPort;
  session.login.email = emailRemetente;
  session.login.password = senhaRemetente;
  session.login.user_domain = "";
  // Defina o tempo de configuração do NTP
  session.time.ntp_server = F("time.google.com"); // Utilizado o NTP do Google:
  //                                                  https://developers.google.com/time
  session.time.gmt_offset = -3; // define o deslocamento em segundos 
  //                                do fuso horário local em relação ao
  //                                GMT do Meridiano de Greenwich.
  
  session.time.day_light_offset = 0; // define o deslocamento em segundos do 
  //                                      fuso horário local. Este valor costuma
  //                                      ser 3600 para horário de verão +1h ou 
  //                                      0 para fusos sem horário de verão.

  // Instanciação do objeto da classe de mensagem
  SMTP_Message message;

  // Definição os cabeçalhos das mensagens
  message.sender.name = nomeRemetente;
  message.sender.email = emailRemetente;
  message.subject = assunto;
  message.addRecipient(nomeDestinatario, emailDestinatario);
  message.text.content = messageTXT.c_str();

  // O conjunto de caracteres de mensagem de texto html, por exemplo:
  //  us-ascii
  //  utf-8
  //  utf-7
  // O valor padrão é utf-8
  message.text.charSet = "utf-8";

  // A codificação de transferência de conteúdo. Ex:
  //  enc_7bit ou "7bit" (não codificado)
  //  enc_qp ou "quoted-printable" (codificado)
  //  enc_base64 ou "base64" (codificado)
  //  enc_binary ou "binary" (não codificado)
  //  enc_8bit ou "8bit" (não codificado)
  //  O valor padrão é "7bit"
  message.text.transfer_encoding = Content_Transfer_Encoding::enc_7bit;

  // A prioridade da mensagem:
  //  esp_mail_smtp_priority_high ou 1
  //  esp_mail_smtp_priority_normal ou 3
  //  esp_mail_smtp_priority_low ou 5
  //  O valor padrão é esp_mail_smtp_priority_low
  message.priority = esp_mail_smtp_priority::esp_mail_smtp_priority_low;

  // As notificações de status de entrega, Ex:
  //  esp_mail_smtp_notify_never
  //  esp_mail_smtp_notify_success
  //  esp_mail_smtp_notify_failure
  //  esp_mail_smtp_notify_delay
  //  O valor padrão é esp_mail_smtp_notify_never
  message.response.notify = esp_mail_smtp_notify_success |
                            esp_mail_smtp_notify_failure |
                            esp_mail_smtp_notify_delay;

  // Conecte-se ao servidor com a configuração da sessão
  if (!smtp.connect(&session))
    return false;

  // Começa a enviar e-mail e fecha a sessão
  if (!MailClient.sendMail(&smtp, &message)) {
    Serial.println("Erro ao enviar e-mail, " + smtp.errorReason());
    return false;
  }
  return true;
}

/** 
 *  Função de retorno de chamada para obter o status de envio de e-mail 
*/
void smtpCallback(SMTP_Status status) {
  // Imprime o status atual
  Serial.println(status.info());

  // Imprima o resultado do envio
  if (status.success()) {
    Serial.println("----------------");
    ESP_MAIL_PRINTF("Mensagem enviada com sucesso: %d\n", status.completedCount());
    ESP_MAIL_PRINTF("Falha na mensagem enviada: %d\n", status.failedCount());
    Serial.println("----------------\n");
    struct tm dt;

    for (size_t i = 0; i < smtp.sendingResult.size(); i++) {
      /* Obter o item de resultado */
      SMTP_Result result = smtp.sendingResult.getItem(i);
      time_t ts = (time_t)result.timestamp;
      localtime_r(&ts, &dt);

      ESP_MAIL_PRINTF("Message No: %d\n", i + 1);
      ESP_MAIL_PRINTF("Status: %s\n", result.completed ? "sucesso" : "fracassado");
      ESP_MAIL_PRINTF("Data/Hora: %d/%d/%d %d:%d:%d\n",
                      dt.tm_year + 1900,
                      dt.tm_mon + 1,
                      dt.tm_mday,
                      dt.tm_hour,
                      dt.tm_min,
                      dt.tm_sec);
      ESP_MAIL_PRINTF("Recebedor: %s\n", result.recipients);
      ESP_MAIL_PRINTF("Sujeito: %s\n", result.subject);
    }
    Serial.println("----------------\n");
  }
}