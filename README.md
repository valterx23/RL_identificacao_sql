# Detecção de Vulnerabilidades SQL Injection com Reinforcement Learning

Trabalho de Graduação (TCC) — Tecnólogo em Segurança da Informação, FATEC Ourinhos.

## Sobre o projeto

Este projeto implementa um agente de Inteligência Artificial baseado em **Q-Learning**
(Reinforcement Learning) capaz de identificar vulnerabilidades de SQL Injection em
aplicações web de forma autônoma, através de interação direta com o alvo sem depender
de assinaturas ou payloads pré-definidos como as ferramentas tradicionais.

O agente aprende, por tentativa e erro, quais estratégias de ataque geram respostas que
indicam vulnerabilidade, recebendo recompensas conforme a eficácia de suas ações.

## Motivação

Scanners tradicionais de SQLi dependem de listas fixas de payloads e assinaturas,
o que limita sua adaptação a variações de contexto e proteções (ex: WAFs, tokens CSRF).
A proposta deste trabalho é avaliar se uma abordagem baseada em Aprendizado por Reforço
consegue generalizar melhor a detecção, aprendendo a política de ataque a partir da
própria interação com a aplicação.

## Bibliotecas e ferramentas utilizadas para o desenvolvimento do projeto

- **Python**
- **Gymnasium** — ambiente customizado de RL
- **Selenium** — automação de interação com a aplicação web
- **Q-Learning** — algoritmo de aprendizado por reforço

## Alvo de testes

O agente foi treinado e avaliado contra o **DVWA (Damn Vulnerable Web Application)**,
nos níveis de segurança MEDIUM e HIGH, hospedado em uma máquina virtual Metasploitable no Virtualbox.

## Resultados
- Taxa de detecção em nível LOW: **74,67%**
- Taxa de detecção em nível MEDIUM: **71,67%**
- Taxa de detecção em nível HIGH: **0%** (impactada pela proteção de token CSRF)
- Treinamento realizado ao longo de 300 episódios

## Como executar

1. Clone o repositório:
```bash
git clone https://github.com/valterx23/RL_identificacao_sql.git
cd RL_identificacao_sql
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Instale Metasploitable no site da rapid7
https://sourceforge.net/projects/metasploitable/

4. Em seguida abra o .iso com virtualbox e na configuração de rede, adicione host-only com IP 192.168.56.1
   Obs: Importante que a máquina esteja com o IP 192.1678.56.101 para o script funcionar via Host-only da máquina virtual metasploitable por virtualbox

6. Execute o script:
```bash
python agente_sql_rl.py
```

## Contexto acadêmico

Este projeto foi desenvolvido como Trabalho de Graduação apresentado à FATEC Ourinhos,
com defesa prevista para dezembro de 2026.


## Licença
Este código é disponibilizado publicamente apenas para fins de portfólio e avaliação
técnica. Não é permitida a reprodução, redistribuição ou uso comercial sem autorização
do autor. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
