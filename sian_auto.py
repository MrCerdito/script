import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import threading
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from preguntas import preguntas
from formato import formato
from selenium.webdriver.support.ui import Select


class SianAutomator:
    def __init__(self, root):
        self.root = root
        root.title("Sian365 - Automatización de Formularios")
        root.geometry("520x230")
        root.resizable(False, False)

        main = ttk.Frame(root, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="Configuración de Automatización", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 15))

        row = 1
        fields = [
            ("URL Base:", "https://app.sian365.co/testsian365"),
            ("Fecha Fin:", "31-12-2026 23:59:59"),
        ]
        self.entries = {}
        for label, default in fields:
            ttk.Label(main, text=label, font=("Segoe UI", 10)).grid(row=row, column=0, sticky=tk.W, pady=4)
            entry = ttk.Entry(main, width=50, font=("Segoe UI", 10))
            entry.insert(0, default)
            entry.grid(row=row, column=1, pady=4, padx=(10, 0))
            self.entries[label] = entry
            row += 1

        self.btn_run = ttk.Button(main, text="▶  Ejecutar Automatización", command=self.run_automation)
        self.btn_run.grid(row=row + 1, column=0, columnspan=2, pady=(20, 5))

        self.status = ttk.Label(main, text="Listo", foreground="gray", font=("Segoe UI", 9))
        self.status.grid(row=row + 2, column=0, columnspan=2)

    def log(self, msg):
        self.status.config(text=msg, foreground="black")
        self.root.update_idletasks()

    def run_automation(self):
        if messagebox.askyesno("Confirmar", "¿Iniciar automatización?"):
            self.btn_run.config(state=tk.DISABLED)
            self.log("Iniciando...")
            threading.Thread(target=self._automate, daemon=True).start()

    def _find_existing_form(self, driver, wait):
        try:
            year = datetime.now().year
            time.sleep(1.5)
            row = driver.find_element(By.XPATH, f"//table[@id='tablaEncuesta']//tr[td[contains(., 'SIMPADE {year}')]]")
            preguntas_btn = row.find_element(By.XPATH, ".//a[i[contains(@class, 'fa-cogs')]]")
            formato_btn = row.find_element(By.XPATH, ".//a[contains(@href, 'for2formato')]")
            return {
                "preguntas_href": preguntas_btn.get_attribute("href"),
                "formato_href": formato_btn.get_attribute("href")
            }
        except:
            return None

    def _count_existing_preguntas(self, driver):
        try:
            hd = driver.find_element(By.ID, "hdSeccionPregunta")
            count = int(hd.get_attribute("value"))
        except:
            count = len(driver.find_elements(By.XPATH, "//div[starts-with(@id, 'seccion_')]"))
        if count == 0:
            return 0
        titulos_existentes = set()
        for i in range(count):
            for id_intentar in [f"txtOpcionPregunta{i}", f"txtTexto{i}", f"txtRecurso{i}", f"txtSeccion{i}", f"txtRecursoTitulo{i}"]:
                try:
                    el = driver.find_element(By.ID, id_intentar)
                    val = el.get_attribute("value").strip()
                    if val:
                        titulos_existentes.add(val)
                    break
                except:
                    continue
        if titulos_existentes:
            faltantes = sum(1 for p in preguntas if p["titulo"] not in titulos_existentes)
            return len(preguntas) - faltantes
        return count

    def _get_existing_formato_contenidos(self, driver):
        try:
            driver.find_element(By.ID, "selFila")
            selectores = [
                "//table[@id='tblContenido']",
                "//table[contains(@id, 'gv')][contains(@id, 'Contenido')]",
                "//table[contains(@class, 'table')][.//th[contains(., 'Contenido')]]",
                "//div[contains(@class, 'table-responsive')]//table",
            ]
            table = None
            for sel in selectores:
                try:
                    table = driver.find_element(By.XPATH, sel)
                    break
                except:
                    continue
            if table is None:
                return None
            rows = table.find_elements(By.XPATH, ".//tr")
            existentes = set()
            for row in rows[1:]:
                cells = row.find_elements(By.TAG_NAME, "td")
                texto = cells[3].text.strip() if len(cells) >= 4 else (cells[-1].text.strip() if cells else "")
                if texto and len(texto) > 3:
                    existentes.add(texto)
            return existentes
        except:
            return None

    def _automate(self):
        driver = None
        try:
            base = self.entries["URL Base:"].get().strip().rstrip("/")
            url_login = base + "/logins.aspx"
            url_form = base + "/for2formulario.aspx"
            username = "superadmin"
            password = "-.1nn0v425--5--"
            titulo = f"SIMPADE {datetime.now().year}"
            fecha_fin = self.entries["Fecha Fin:"].get().strip()
            orden = "1"

            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
            wait = WebDriverWait(driver, 15)

            self.log("Cargando página de login...")
            driver.get(url_login)

            self.log("Ingresando credenciales...")
            wait.until(EC.presence_of_element_located((By.ID, "txtUsuario"))).send_keys(username)
            driver.find_element(By.ID, "txtPass").send_keys(password)
            driver.find_element(By.ID, "btnEntrar").click()

            wait.until(lambda d: d.current_url != url_login)
            self.log("Login exitoso")

            self.log("Buscando formulario SIMPADE existente...")
            driver.get(url_form)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            existing = self._find_existing_form(driver, wait)

            if existing:
                self.log(f"Formulario '{titulo}' encontrado. Continuando con lo que falte...")
                driver.get(existing["preguntas_href"])
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(0.5)
                self._crear_preguntas(driver, wait)

                self.log("Configurando formato faltante...")
                driver.get(existing["formato_href"])
                wait.until(EC.presence_of_element_located((By.ID, "selFila")))
                time.sleep(0.5)
                self._configurar_formato(driver, wait)
            else:
                self.log(f"Formulario '{titulo}' no existe. Creando nuevo...")
                self._crear_nuevo_formulario(driver, wait, base, titulo, fecha_fin, orden)

                self.log("Abriendo Configurar preguntas...")
                wait.until(EC.element_to_be_clickable((By.XPATH, "//a[i[@title='Configurar preguntas']]"))).click()
                time.sleep(2)
                if len(driver.window_handles) > 1:
                    driver.switch_to.window(driver.window_handles[-1])
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

                self._crear_preguntas(driver, wait)

                self.log("Configurando formato...")
                self._configurar_formato(driver, wait)

            self.log("Proceso completado exitosamente")
            self.status.config(text="¡Completado! Formulario verificado y actualizado.", foreground="green")

        except Exception as e:
            self.log(f"Error: {str(e)}")
            messagebox.showerror("Error", str(e))
        finally:
            self.btn_run.config(state=tk.NORMAL)
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def _crear_nuevo_formulario(self, driver, wait, base, titulo, fecha_fin, orden):
        self.log("Abriendo Nuevo Formulario...")
        wait.until(EC.element_to_be_clickable((By.ID, "aBtnNuevoFormulario"))).click()
        wait.until(EC.visibility_of_element_located((By.ID, "txtTitulo")))

        driver.find_element(By.ID, "txtTitulo").send_keys(titulo)
        self.log(f"Título: {titulo}")

        ahora = datetime.now()
        driver.find_element(By.ID, "txtFechaInicio").clear()
        driver.find_element(By.ID, "txtFechaInicio").send_keys(ahora.strftime("%d-%m-%Y") + " 00:00:00")
        self.log("Fecha inicio establecida")

        driver.find_element(By.ID, "txtFechaFin").clear()
        driver.find_element(By.ID, "txtFechaFin").send_keys(fecha_fin)
        self.log(f"Fecha fin: {fecha_fin}")

        checkboxes = driver.find_elements(By.CSS_SELECTOR, "#rdTiposUsuarios input[type='checkbox']")
        for cb in checkboxes:
            cb_id = cb.get_attribute("id")
            debe = cb_id in {"rdTiposUsuarios_1", "rdTiposUsuarios_5"}
            esta = cb.is_selected()
            if debe and not esta:
                driver.execute_script("arguments[0].click()", cb)
            elif not debe and esta:
                driver.execute_script("arguments[0].click()", cb)
        self.log("Perfiles: Estudiante y Padres")

        driver.find_element(By.ID, "txtOrden").send_keys(orden)
        self.log(f"Orden: {orden}")

        driver.find_element(By.ID, "btnGuardarEncuesta").click()
        self.log("Esperando a que se guarde el formulario...")
        wait.until(EC.element_to_be_clickable((By.ID, "aBtnNuevoFormulario")))

    def _configurar_formato(self, driver, wait):
        try:
            existentes = self._get_existing_formato_contenidos(driver)
            if existentes:
                self.log(f"Entradas existentes detectadas: {len(existentes)}")
        except:
            existentes = None

        agregadas = 0
        for i, f in enumerate(formato):
            if existentes and f["contenido"].strip() in existentes:
                continue

            self.log(f"Formato {i + 1}/{len(formato)}: {f['contenido'][:40]}...")

            try:
                Select(driver.find_element(By.ID, "selFila")).select_by_value(f["fila"])
                inp_orden = driver.find_element(By.ID, "txtOrden")
                inp_orden.clear()
                inp_orden.send_keys(f["orden"])
                Select(driver.find_element(By.ID, "selTamano")).select_by_value(f["tamano"])
                Select(driver.find_element(By.ID, "selTipoContenido")).select_by_visible_text(
                    "Texto" if f["tipo"] == "texto" else "Pregunta"
                )
                time.sleep(0.2)

                if f["tipo"] == "texto":
                    driver.execute_script(
                        "document.querySelector('textarea[name=\"txtContenido\"]').value = arguments[0]",
                        f["contenido"]
                    )
                else:
                    s = Select(driver.find_element(By.ID, "selPreguntas"))
                    opciones_disponibles = [o.text.strip() for o in s.options if o.text.strip()]
                    if f["contenido"] not in opciones_disponibles:
                        self.log(f"  '{f['contenido'][:40]}' ya existe en el formato, saltando...")
                        continue
                    s.select_by_visible_text(f["contenido"])

                btn_agregar = driver.find_element(By.ID, "btnAgregarPregunta")
                if btn_agregar.is_enabled():
                    btn_agregar.click()
                    agregadas += 1
                    time.sleep(0.3)
                else:
                    self.log(f"  Botón deshabilitado, saltando...")
            except Exception as e:
                self.log(f"  Error agregando '{f['contenido'][:30]}': {str(e)[:50]}")

        self.log(f"Formato: {agregadas} entradas agregadas ({len(formato) - agregadas} ya existían)")

    def _crear_preguntas(self, driver, wait):
        existing = self._count_existing_preguntas(driver)
        if existing >= len(preguntas):
            self.log(f"Todas las {len(preguntas)} preguntas ya existen")
            return

        if existing > 0:
            self.log(f"{existing} preguntas existentes detectadas, creando {len(preguntas) - existing} faltantes...")

        section = existing
        for idx in range(existing, len(preguntas)):
            p = preguntas[idx]
            tipo = p["tipo"]
            titulo = p["titulo"]

            self.log(f"Pregunta {idx + 1}/{len(preguntas)}: {titulo[:45]}...")

            driver.execute_script(f"abrirSeccionPregunta('{tipo}', null, true)")
            wait.until(EC.presence_of_element_located((By.ID, f"seccion_{section}")))
            time.sleep(0.2)

            if tipo == "recurso":
                sec_html = driver.find_element(By.ID, f"seccion_{section}").get_attribute("outerHTML")
                with open(f"debug_recurso.html", "w", encoding="utf-8") as f:
                    f.write(sec_html)

            for id_intentar in [f"txtOpcionPregunta{section}", f"txtTexto{section}", f"txtRecurso{section}", f"txtSeccion{section}", f"txtRecursoTitulo{section}"]:
                try:
                    if "txtRecurso" in id_intentar:
                        driver.execute_script("""
                            var el = document.getElementById(arguments[0]);
                            el.value = arguments[1];
                            $(el).trigger('change');
                        """, id_intentar, titulo)
                    else:
                        inp = driver.find_element(By.ID, id_intentar)
                        inp.clear()
                        inp.send_keys(titulo)
                    break
                except:
                    continue

            if tipo == "opcion" and "opciones" in p:
                opts = p["opciones"]
                for i, txt in enumerate(opts):
                    num = i + 1
                    if num <= 2:
                        try:
                            el = driver.find_element(By.ID, f"txtOpcion{num}-{section}")
                            el.clear()
                            el.send_keys(txt)
                        except:
                            pass
                    else:
                        try:
                            btn = wait.until(EC.presence_of_element_located((By.ID, f"btn_agregar_opcion_{section}")))
                            driver.execute_script("arguments[0].click()", btn)
                            time.sleep(0.2)
                            el = wait.until(EC.presence_of_element_located((By.ID, f"txtOpcion{num}-{section}")))
                            el.clear()
                            el.send_keys(txt)
                        except:
                            pass

            if p.get("varias", False):
                try:
                    chk = driver.find_element(By.ID, f"chk_varias_respuesta_opciones_{section}")
                    if not chk.is_selected():
                        driver.execute_script("arguments[0].click()", chk)
                except:
                    pass

            if p.get("enteros", False):
                try:
                    sec = driver.find_element(By.ID, f"seccion_{section}")
                    toggle = sec.find_element(By.CSS_SELECTOR, ".dropdown-toggle")
                    driver.execute_script("arguments[0].click()", toggle)
                    time.sleep(0.15)
                    el = driver.find_element(By.ID, f"numeros_enteros_{section}")
                    driver.execute_script("arguments[0].click()", el)
                except:
                    pass

            try:
                chk = driver.find_element(By.ID, f"chk_obligatoria_{section}")
                if not chk.is_selected():
                    driver.execute_script("arguments[0].click()", chk)
            except:
                pass

            section += 1

        if section > existing:
            self.log("Guardando preguntas nuevas...")
            try:
                driver.execute_script("guardarSecciones()")
                time.sleep(0.5)
            except Exception as e:
                self.log(f"Error al guardar preguntas: {str(e)[:50]}")
                messagebox.showwarning("Guardado", f"Error al guardar preguntas: {str(e)[:50]}")
            self.log(f"{section - existing} preguntas creadas")
        else:
            self.log("No se crearon preguntas nuevas")


if __name__ == "__main__":
    root = tk.Tk()
    app = SianAutomator(root)
    root.mainloop()
