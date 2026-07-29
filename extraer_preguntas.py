import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import threading
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


class ExtraerPreguntas:
    def __init__(self, root):
        self.root = root
        root.title("Extraer Preguntas - Sian365")
        root.geometry("540x280")
        root.resizable(False, False)

        main = ttk.Frame(root, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="Extraer Preguntas de Formulario", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 15))

        row = 1
        fields = [
            ("URL Login:", "https://cloud.sian365.co/lahacienda/logins.aspx"),
            ("URL Form:", "https://cloud.sian365.co/lahacienda/for2formulario.aspx"),
        ]
        self.entries = {}
        for label, default in fields:
            ttk.Label(main, text=label, font=("Segoe UI", 10)).grid(row=row, column=0, sticky=tk.W, pady=4)
            entry = ttk.Entry(main, width=55, font=("Segoe UI", 10))
            entry.insert(0, default)
            entry.grid(row=row, column=1, pady=4, padx=(10, 0))
            self.entries[label] = entry
            row += 1

        ttk.Label(main, text="Credenciales:", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=(10, 0))
        row += 1
        ttk.Label(main, text="superadmin / -.1nn0v425--5--", font=("Segoe UI", 9), foreground="gray").grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        row += 1

        self.btn_run = ttk.Button(main, text="▶  Extraer Preguntas", command=self.run_extraction)
        self.btn_run.grid(row=row, column=0, columnspan=2, pady=(10, 5))
        row += 1

        self.status = ttk.Label(main, text="Listo", foreground="gray", font=("Segoe UI", 9))
        self.status.grid(row=row, column=0, columnspan=2)

    def log(self, msg):
        self.status.config(text=msg, foreground="black")
        self.root.update_idletasks()

    def run_extraction(self):
        if messagebox.askyesno("Confirmar", "Iniciar extraccion de preguntas?"):
            self.btn_run.config(state=tk.DISABLED)
            self.log("Iniciando...")
            threading.Thread(target=self._extract, daemon=True).start()

    def _extract(self):
        try:
            url_login = self.entries["URL Login:"].get().strip()
            url_form = self.entries["URL Form:"].get().strip()
            username = "superadmin"
            password = "-.1nn0v425--5--"

            options = Options()
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            wait = WebDriverWait(driver, 20)

            self.log("Cargando pagina de login...")
            driver.get(url_login)

            self.log("Ingresando credenciales...")
            wait.until(EC.presence_of_element_located((By.ID, "txtUsuario"))).send_keys(username)
            driver.find_element(By.ID, "txtPass").send_keys(password)
            driver.find_element(By.ID, "btnEntrar").click()

            wait.until(lambda d: d.current_url != url_login)
            self.log("Login exitoso")

            self.log("Navegando al formulario...")
            driver.get(url_form)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            self.log("Buscando formulario con Configurar preguntas...")
            config_links = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//a[i[@title='Configurar preguntas']]")))
            if not config_links:
                raise Exception("No se encontro ningun boton 'Configurar preguntas'")

            link = config_links[0]
            href = link.get_attribute("href")
            self.log(f"Abriendo configuracion de preguntas...")
            link.click()

            self.log("Cargando pagina de preguntas...")
            driver.switch_to.window(driver.window_handles[-1])
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            self.log("Extrayendo informacion de preguntas...")
            resultado = self._analizar_pagina(driver, wait)

            self.log("Guardando archivo...")
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            filename = f"preguntas_extraidas_{timestamp}.txt"
            filepath = os.path.join(os.path.dirname(__file__), filename) if "__file__" in dir() else filename
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(resultado)

            self.status.config(text=f"Archivo guardado: {filename}", foreground="green")
            messagebox.showinfo("Completado", f"Preguntas extraidas correctamente.\nArchivo: {filename}")

        except Exception as e:
            self.log(f"Error: {str(e)}")
            messagebox.showerror("Error", str(e))
        finally:
            self.btn_run.config(state=tk.NORMAL)

    def _analizar_pagina(self, driver, wait):
        lines = []
        lines.append("=" * 60)
        lines.append(f"EXTRACCION DE PREGUNTAS - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append(f"URL: {driver.current_url}")
        lines.append(f"Titulo: {driver.title}")
        lines.append("")

        page_source = driver.page_source
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = os.path.join(os.path.dirname(__file__) if "__file__" in dir() else ".", f"page_source_{ts}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(page_source)
        lines.append(f"[HTML guardado en: {html_path}]")
        lines.append("")

        preguntas = self._find_questions(driver)
        if preguntas:
            lines.append(f"Se encontraron {len(preguntas)} preguntas:")
            lines.append("")
            for i, p in enumerate(preguntas, 1):
                lines.append(f"--- Pregunta {i} ---")
                for key, val in p.items():
                    lines.append(f"  {key}: {val}")
                lines.append("")
        else:
            lines.append("NO SE ENCONTRARON PREGUNTAS CON LOS SELECTORES CONOCIDOS.")
            lines.append("")
            lines.append("--- TEXTO VISIBLE DE LA PAGINA ---")
            lines.append("")

            body = driver.find_element(By.TAG_NAME, "body")
            text = body.text
            lines.append(text)

        lines.append("=" * 60)
        lines.append("FIN DEL REPORTE")
        lines.append("=" * 60)
        return "\n".join(lines)

    def _find_questions(self, driver):
        preguntas = []

        tablas = driver.find_elements(By.XPATH, "//table")
        for tabla in tablas:
            filas = tabla.find_elements(By.XPATH, ".//tr")
            for fila in filas:
                celdas = fila.find_elements(By.XPATH, ".//td | .//th")
                if len(celdas) >= 2:
                    datos = {}
                    for j, celda in enumerate(celdas):
                        datos[f"col_{j+1}"] = celda.text.strip()
                    if any(datos.values()):
                        inputs = fila.find_elements(By.XPATH, ".//input | .//select | .//textarea")
                        for inp in inputs:
                            tag = inp.tag_name
                            name = inp.get_attribute("name") or ""
                            val = inp.get_attribute("value") or ""
                            tipo = inp.get_attribute("type") or ""
                            if tag == "input" and tipo in ("radio", "checkbox"):
                                label_elem = driver.execute_script(
                                    "return arguments[0].closest('label') ? arguments[0].closest('label').textContent : ''", inp
                                ) or inp.get_attribute("data-label") or ""
                                checked = inp.is_selected()
                                datos[f"input_{name or len(datos)}"] = f"[{'X' if checked else ' '}] {label_elem or val}"
                            elif tag == "select":
                                selected = inp.find_elements(By.XPATH, ".//option[@selected]")
                                opts = [o.text for o in inp.find_elements(By.XPATH, ".//option")]
                                datos[f"select_{name or len(datos)}"] = f"Opciones: {', '.join(opts)}"
                        preguntas.append(datos)

        divs_pregunta = driver.find_elements(By.XPATH, "//div[contains(@class, 'pregunta') or contains(@id, 'pregunta') or contains(@class, 'question') or contains(@id, 'question')]")
        for div in divs_pregunta:
            texto = div.text.strip()
            if texto and len(texto) > 5:
                inputs = div.find_elements(By.XPATH, ".//input | .//select | .//textarea")
                datos = {"texto": texto}
                opciones = []
                for inp in inputs:
                    tipo = inp.get_attribute("type") or ""
                    if tipo in ("radio", "checkbox"):
                        label = driver.execute_script(
                            "return arguments[0].closest('label') ? arguments[0].closest('label').textContent : ''", inp
                        ).strip() or inp.get_attribute("value") or ""
                        checked = inp.is_selected()
                        opciones.append(f"[{'X' if checked else ' '}] {label}")
                    elif tipo == "text":
                        val = inp.get_attribute("value") or ""
                        if val:
                            opciones.append(f"Texto: {val}")
                if opciones:
                    datos["opciones"] = "; ".join(opciones)
                preguntas.append(datos)

        labels = driver.find_elements(By.TAG_NAME, "label")
        for label in labels:
            texto = label.text.strip()
            if texto and len(texto) > 10:
                for_id = label.get_attribute("for") or ""
                inp = None
                if for_id:
                    try:
                        inp = driver.find_element(By.ID, for_id)
                    except:
                        pass
                if inp:
                    tipo = inp.get_attribute("type") or inp.tag_name
                    datos = {"texto": texto, "tipo": tipo}
                    if tipo in ("radio", "checkbox"):
                        checked = inp.is_selected()
                        datos["estado"] = "Seleccionado" if checked else "No seleccionado"
                    elif tipo == "text":
                        datos["valor"] = inp.get_attribute("value") or ""
                    preguntas.append(datos)

        if not preguntas:
            forms = driver.find_elements(By.TAG_NAME, "form")
            for form in forms:
                fname = form.get_attribute("name") or form.get_attribute("id") or ""
                ftext = form.text.strip()
                if ftext:
                    preguntas.append({"form": fname or "sin_nombre", "html": ftext[:500]})

        return preguntas


if __name__ == "__main__":
    root = tk.Tk()
    app = ExtraerPreguntas(root)
    root.mainloop()
