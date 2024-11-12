from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import pandas as pd
import chromedriver_autoinstaller
import logging
import mysql.connector
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Detalhes de conexão com o banco de dados
host = 'srv1069.hstgr.io'
user = 'u390885117_admin'
password = ':tOiwdfP7aX'
database = 'u390885117_comentarios'

# Opções do Chrome
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument('--log-level=3')
chrome_options.add_argument('--blink-settings=imagesEnabled=false')


def create_driver():
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(120)  # Timeout de 2 minutos
    return driver


def process_url(url, thread_id):
    driver = create_driver()
    data_processada = []
    try:
        logging.info(f"Thread {thread_id} - Processando: {url}")
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "perguntas")))

        link = driver.current_url
        nome = driver.find_element(By.CSS_SELECTOR, 'header h1').text
        codigo_anuncio = driver.find_element(By.CSS_SELECTOR, '.info-visualizacao > span').text
        link_loja = driver.find_element(By.CSS_SELECTOR, '.indique-amigo a').get_attribute('href')

        perguntas = driver.find_elements(By.CSS_SELECTOR, '.pergunta')
        for pergunta in perguntas:
            try:
                data_pergunta = pergunta.find_element(By.CSS_SELECTOR, '.data').text
                conteudo_pergunta = pergunta.find_elements(By.CSS_SELECTOR, 'p')[-1].text

                resposta = pergunta.find_elements(By.XPATH, '../div[@class="resposta"]')
                data_resposta = resposta[0].find_element(By.CSS_SELECTOR, '.data').text if resposta else ''
                conteudo_resposta = resposta[0].find_elements(By.CSS_SELECTOR, 'p')[-1].text if resposta else ''

                data_processada.append({
                    'link': link,
                    'nome': nome,
                    'codigo_anuncio': codigo_anuncio,
                    'data': data_pergunta,
                    'comentario': conteudo_pergunta,
                    'resposta': f'{data_resposta} - {conteudo_resposta}',
                    'link_loja': link_loja
                })
            except NoSuchElementException as e:
                logging.warning(f"Thread {thread_id} - Elemento não encontrado em {url}: {e}")
    except TimeoutException:
        logging.warning(f"Thread {thread_id} - Timeout ocorreu para URL: {url}")
    except Exception as e:
        logging.error(f"Thread {thread_id} - Erro processando URL {url}: {str(e)}")
    finally:
        driver.quit()
    return data_processada


def insert_data(data):
    conn = mysql.connector.connect(host=host, user=user, password=password, database=database)
    cursor = conn.cursor()
    nome_tabela = 'registros'
    total_registros = len(data)
    registros_inseridos = 0
    registros_existentes = 0
    
    for i, row in enumerate(data):
        try:
            # Tratamento de erros de conversão de data
            try:
                formatted_datetime = pd.to_datetime(row['data'], format='%d/%m/%Y %H:%M:%S', errors='raise').strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                logging.warning(f"Data inválida ignorada: {row['data']}")
                continue

            cursor.execute(
                f"SELECT id FROM {nome_tabela} WHERE codigo_anuncio = %s AND data = %s AND comentario = %s",
                (row['codigo_anuncio'], formatted_datetime, row['comentario']))

            if cursor.fetchone() is None:
                cursor.execute(
                    f"INSERT INTO {nome_tabela} (link, nome, codigo_anuncio, data, comentario, resposta, link_loja)"
                    f" VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (row['link'], row['nome'], row['codigo_anuncio'], formatted_datetime, row['comentario'],
                     row['resposta'], row['link_loja']))
                registros_inseridos += 1
                logging.info(f"Inserido: {row['codigo_anuncio']} ({i+1}/{total_registros})")
            else:
                registros_existentes += 1
                logging.info(f"Já existe: {row['codigo_anuncio']} ({i+1}/{total_registros})")
        except Exception as e:
            logging.error(f"Erro ao inserir dados: {str(e)}")

    cursor.execute(f"INSERT INTO logs (data) VALUES (NOW() - INTERVAL 3 HOUR);")
    conn.commit()
    conn.close()
    logging.info(f"Resumo da inserção: Inseridos={registros_inseridos}, Existentes={registros_existentes}, Total={total_registros}")


def get_product_links():
    links = []
    driver = create_driver()
    try:
        url_base = "https://www.mfrural.com.br/busca/trilhos?pg="
        pagina = 1
        while True:
            url = url_base + str(pagina)
            driver.get(url)
            logging.info(f"Tentando a página: {url}")

            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.products__container-link')))
            except TimeoutException:
                logging.warning(f"Timeout na página {pagina}, indo para a próxima página")
                pagina += 1
                continue

            try:
                no_data_message = driver.find_element(By.XPATH, '//p[text()="Nenhum dado foi retornado."]')
                if no_data_message.is_displayed():
                    logging.info("Última página encontrada")
                    break
            except NoSuchElementException:
                pass

            produtos = driver.find_elements(By.CSS_SELECTOR, '.products__container-link')
            for i, produto in enumerate(produtos):
                url = produto.get_attribute('href')
                if url:
                    logging.info(f"Link encontrado na página {pagina} ({i+1}/{len(produtos)}): {url}")
                    links.append(url)

            pagina += 1
    except Exception as e:
        logging.error(f"Erro ao obter links de produtos: {str(e)}")
    finally:
        driver.quit()
    return links


def main():
    while True:
        links = get_product_links()
        total_links = len(links)
        logging.info(f"Total de links encontrados: {total_links}")

        if not links:  # Sai do loop se não houver links
            logging.info("Nenhum link encontrado. Finalizando...")
            break

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_url = {executor.submit(process_url, url, i): url for i, url in enumerate(links)}
            all_data = []
            for i, future in enumerate(as_completed(future_to_url)):
                url = future_to_url[future]
                try:
                    data = future.result()
                    all_data.extend(data)
                    logging.info(f"Dados processados de {url} ({i+1}/{total_links})")
                except Exception as e:
                    logging.error(f"Erro ao processar {url}: {str(e)}")

        if all_data:
            insert_data(all_data)

        logging.info("Dormindo por 1 minuto antes da próxima iteração")
        time.sleep(60)


if __name__ == "__main__":
    main()