import customtkinter as ctk
import tkinter as tk
import os
from customtkinter import *
from tkinter import messagebox, font, PhotoImage
from datetime import datetime
from PIL import Image, ImageTk
import time
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from google.api_core.exceptions import GoogleAPICallError

# Inicializar o Firebase
cred = credentials.Certificate("cdaserver-firebase-adminsdk-1wv4x-9bbf23a34a.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def init_db():
# Verificar se o usuário administrador já existe
    usuarios_ref = db.collection('usuarios')
    admin_user = usuarios_ref.where('username', '==', 'admin').stream()
    if not any(admin_user):
        usuarios_ref.add({
            'username': 'admin',
            'password': 'admin'
        })

# Inicializa o banco de dados
init_db()

canvas_usuario = None
canvas = None
frame_tarefas_usuario_interior = None


# Função para marcar a tarefa como de alta prioridade
def definir_alta_prioridade(tarefa_id):
    try:
        # Atualiza o documento da tarefa no Firebase para marcar como alta prioridade
        db.collection('tarefas').document(tarefa_id).update({
            'alta_prioridade': True,
            'timestamp_prioridade': firestore.SERVER_TIMESTAMP  # Atualiza o timestamp para garantir que fique no topo
        })
        atualizar_lista_tarefas()
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao definir alta prioridade: {e}")

# Função para adicionar tarefa
def adicionar_tarefa(event=None):
    tarefa = entrada_tarefa.get("1.0", ctk.END).strip()

    if tarefa:
        try:
            db.collection('tarefas').add({
                'tarefa': tarefa,
                'data_check': None,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'alta_prioridade': False  # Nova tarefa inicia sem alta prioridade
            })
            entrada_tarefa.delete("1.0", ctk.END)
            atualizar_lista_tarefas()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao adicionar tarefa: {e}")
    else:
        messagebox.showwarning("Aviso", "A tarefa não pode estar vazia.")

# Função para atualizar a lista de tarefas
def atualizar_lista_tarefas():
    for widget in frame_tarefas_usuario_interior.winfo_children():
        widget.destroy()
  
    tarefas_ref = db.collection('tarefas').order_by('alta_prioridade', direction=firestore.Query.DESCENDING).order_by('timestamp', direction=firestore.Query.DESCENDING)

    for doc in tarefas_ref.stream():
        
        tarefa_data = doc.to_dict()
        cor_frame = "#333333"
        tarefa_frame = ctk.CTkFrame(frame_tarefas_usuario_interior, fg_color="#333333", corner_radius=0)
        tarefa_frame.pack(fill="x", pady=3)

        tarefa_label = ctk.CTkLabel(tarefa_frame, text=tarefa_data['tarefa'], anchor="w", fg_color="#333333", text_color="#ffffff", font=("Segoe UI Variable Display", 15), justify="left")
        tarefa_label.pack(side="left", padx=(5,50), pady=15, fill="x", expand=True)

        if tarefa_data['data_check']:
            check_label = ctk.CTkLabel(tarefa_frame, anchor ="s", text=f"Concluída: {tarefa_data['data_check']}", fg_color="#333333", text_color="darkgray", font=("Segoe UI Variable Display", 12))
            check_label.pack(side="left", padx=(10,1), pady=(24, 1))

            delete_button = ctk.CTkButton(tarefa_frame, anchor ="s", width=50, height=55, hover_color="#5d5e5e", text="Excluir", command=lambda id=doc.id: excluir_tarefa(id), fg_color="#333333", text_color="darkgray", corner_radius=1, font=("Segoe UI Variable Display", 10))
            delete_button.pack(side="right", padx=5, pady=1)

        else:
            check_button = ctk.CTkButton(tarefa_frame, anchor ="s", width=50, height=55, hover_color="#004c4c", text="Check", command=lambda id=doc.id: concluir_tarefa(id), fg_color="#333333", text_color="darkgray", corner_radius=1, font=("Segoe UI Variable Display", 10))
            check_button.pack(side="left", padx=1, pady=1)

            edit_button = ctk.CTkButton(tarefa_frame, anchor ="s", width=50, height=55, hover_color="#5d5e5e", text="Editar", command=lambda id=doc.id: editar_tarefa(id), fg_color="#333333", text_color="darkgray", corner_radius=1, font=("Segoe UI Variable Display", 10))
            edit_button.pack(side="left", padx=1, pady=1)

            delete_button = ctk.CTkButton(tarefa_frame, anchor ="s", width=50, height=55, hover_color="#5d5e5e", text="Excluir", command=lambda id=doc.id: excluir_tarefa(id), fg_color="#333333", text_color="darkgray", corner_radius=1, font=("Segoe UI Variable Display", 10))
            delete_button.pack(side="left", padx=1, pady=1)

            prioridade_button = ctk.CTkButton(tarefa_frame, anchor ="s", width=25, height=55, hover_color="#5d5e5e", text="AP", 
                                              command=lambda id=doc.id: definir_alta_prioridade(id), 
                                              fg_color="#780202" if tarefa_data.get('alta_prioridade', False) else cor_frame, 
                                              text_color="darkgray", corner_radius=1, font=("Segoe UI Variable Display", 10))
            prioridade_button.pack(side="right", padx=5, pady=1)

    # Atualiza o tamanho do frame interno
    frame_tarefas_usuario_interior.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))
    canvas.config(width=canvas.winfo_width(), height=canvas.winfo_height())



# Função para marcar tarefa como concluída
def concluir_tarefa(id):
    data_check = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    try:
        db.collection('tarefas').document(id).update({
            'data_check': data_check
        })
        atualizar_lista_tarefas()
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao concluir tarefa: {e}")

# Função para excluir tarefa
def excluir_tarefa(id):
    try:
        db.collection('tarefas').document(id).delete()
        atualizar_lista_tarefas()
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao excluir tarefa: {e}")

# Função para editar tarefa
def editar_tarefa(id):
    def atualizar_tarefa():
        nova_tarefa = entrada_editar_tarefa.get("1.0", ctk.END).strip()
        if nova_tarefa:
            try:
                db.collection('tarefas').document(id).update({
                    'tarefa': nova_tarefa
                })
                janela_editar.destroy()
                atualizar_lista_tarefas()
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao editar tarefa: {e}")
        else:
            messagebox.showwarning("Aviso", "A tarefa não pode estar vazia.")


    janela_editar = ctk.CTk() # Use tkinter Toplevel
    janela_editar.title("Editar Tarefa")
    janela_editar.title("Editar Tarefa")
    janela_editar.geometry("420x380")
    janela_editar.configure(bg="#262626")

    # Definir ícone usando tkinter
    janela_editar.iconbitmap("CDA.ico")

    # Converter o Toplevel para um objeto CustomTkinter
    ctk_frame_editar = ctk.CTkFrame(janela_editar, corner_radius=0)
    ctk_frame_editar.pack(padx=5, pady=5, fill="both", expand=True)

    ctk.CTkLabel(ctk_frame_editar, text="", fg_color="#262626", text_color="#ffffff", font=("Segoe UI Variable Display", 12)).grid(row=0, column=0, pady=5, padx=5)

    entrada_editar_tarefa = ctk.CTkTextbox(ctk_frame_editar, height=300, width=400, fg_color="#333333", text_color="#ffffff", font=("Segoe UI Variable Display", 14))
    entrada_editar_tarefa.grid(row=0, column=0, pady=5, padx=5)
    ## entrada_tarefa.pack(side="left", fill="both", expand=True)

    # Preenche o campo de texto com a tarefa existente
    tarefa_data = db.collection('tarefas').document(id).get().to_dict()
    entrada_editar_tarefa.insert(ctk.END, tarefa_data['tarefa'])

    botao_atualizar = ctk.CTkButton(ctk_frame_editar, text="Atualizar", command=atualizar_tarefa, fg_color="#008080", hover_color="#02a1a1", text_color="white", corner_radius=1, font=("Segoe UI Variable Display", 13))
    botao_atualizar.grid(row=2, column=0, pady=10, padx=5)

    janela_editar.mainloop()

# Função para lidar com o evento de scroll do mouse
def handle_mousewheel(event):
    canvas.yview_scroll(int(-1*(event.delta/120)), "units")


# FUNÇÃO PARA EXIBIR JANELA DE GERENCIAMENTO DO ADMINISTRADOR 


def exibir_gerenciamento_admin():
    global janela_admin, frame_tarefas_usuario_interior, canvas_usuario, canvas

    janela_admin = ctk.CTk()
    janela_admin.title("Gerenciamento de Usuários")
    janela_admin.geometry("400x400")
    janela_admin.after(250, lambda: janela_admin.iconbitmap('CDA.ico'))

    # Exibi a lista de usuários
    def atualizar_lista_usuarios():
        for widget in frame_tarefas_usuario_interior.winfo_children():
            widget.destroy()

        usuarios_ref = db.collection('usuarios').order_by('username').stream()
        for doc in usuarios_ref:
            user_data = doc.to_dict()
            usuario_frame = ctk.CTkFrame(frame_tarefas_usuario_interior, fg_color="#333333", corner_radius=0)
            usuario_frame.pack(fill="x", pady=2)

            usuario_label = ctk.CTkLabel(usuario_frame, text=user_data['username'], anchor="w", fg_color="#333333", text_color="#ffffff", font=("Segoe UI Semibold", 15))
            usuario_label.pack(side="left", padx=10, pady=5, fill="x", expand=True)

            gerenciar_button = ctk.CTkButton(usuario_frame, width=100, text="Gerenciar", command=lambda user_id=doc.id: gerenciar_usuario(user_id), fg_color="#616e81", text_color="white", hover_color="#a3a3a3", corner_radius=1, font=("Segoe UI Variable Display", 12))
            gerenciar_button.pack(side="right", padx=10, pady=5)


# Função para gerenciamento de usuário específico
    def gerenciar_usuario(user_id):
        global frame_tarefas_usuario_interior, canvas_usuario, canvas

        doc = db.collection('usuarios').document(user_id).get()
        user_data = db.collection('usuarios').document(user_id).get().to_dict()
        username = user_data['username']

        def adicionar_tarefa_usuario():
            tarefa = entrada_tarefa_usuario.get("1.0", ctk.END).strip()
            if tarefa:
                try:
                    print(f"Adicionando tarefa para o usuário: {username}")  # Verifica o nome do usuário
                    db.collection('tarefas').add({
                        'tarefa': tarefa,
                        'username': username,
                        'data_check': None,
                        'alta_prioridade': False,
                        'timestamp': firestore.SERVER_TIMESTAMP
                    })
                    entrada_tarefa_usuario.delete("1.0", ctk.END)
                    atualizar_lista_tarefas_usuario()
                except GoogleAPICallError as e:
                    messagebox.showerror("Erro", f"Erro ao adicionar tarefa: {e}")
            else:
                messagebox.showwarning("Aviso", "A tarefa não pode estar vazia.")

        # atualizar lista de tarefas do administrador para outros usuários
        def atualizar_lista_tarefas_usuario():
            global canvas_usuario, canvas

            for widget in frame_tarefas_usuario_interior.winfo_children():
                widget.destroy()

            tarefas_ref = db.collection('tarefas').where('username', '==', username).order_by('timestamp', direction=firestore.Query.DESCENDING).stream()

            for doc in tarefas_ref:
                tarefa_data = doc.to_dict()
                cor_frame = "#333333"
                tarefa_frame = ctk.CTkFrame(frame_tarefas_usuario_interior, fg_color="#333333", corner_radius=0)
                tarefa_frame.pack(fill="x", pady=3)

                tarefa_label = ctk.CTkLabel(tarefa_frame, text=tarefa_data['tarefa'], anchor="w", fg_color="#333333", text_color="#ffffff", font=("Segoe UI Variable Display", 15), justify="left")
                tarefa_label.pack(side="left", padx=(5,50), pady=15, fill="x", expand=True)

                if tarefa_data['data_check']:
                    check_label = ctk.CTkLabel(tarefa_frame, anchor ="s", text=f"Conslusão: {tarefa_data['data_check']}", fg_color="#333333", text_color="#cccccc", font=("Segoe UI Variable Display", 12))
                    check_label.pack(side="left", padx=(10,1), pady=(24, 1))

                    delete_button = ctk.CTkButton(tarefa_frame, anchor ="s", width=50, height=50, text="Excluir", command=lambda id=doc.id: excluir_tarefa(id), fg_color="#333333", hover_color="#5d5e5e", text_color="darkgray", corner_radius=1, font=("Segoe UI Variable Display", 10))
                    delete_button.pack(side="right", padx=(0, 2), pady=2)
                else:
                    check_button = ctk.CTkButton(tarefa_frame, anchor ="s", width=50, height=50, text="Check", command=lambda id=doc.id: concluir_tarefa(id), fg_color="#333333", hover_color="#004c4c", text_color="darkgray", corner_radius=1, font=("Segoe UI Variable Display", 10))
                    check_button.pack(side="left", padx=(0, 2), pady=5)

                    edit_button = ctk.CTkButton(tarefa_frame, anchor ="s", width=50, height=50, text="Editar", command=lambda id=doc.id: editar_tarefa(id), fg_color="#333333", hover_color="#5d5e5e", text_color="darkgray", corner_radius=1, font=("Segoe UI Variable Display", 10))
                    edit_button.pack(side="left", padx=(0, 2), pady=5)

                    delete_button = ctk.CTkButton(tarefa_frame, anchor ="s", width=50, height=50, text="Excluir", command=lambda id=doc.id: excluir_tarefa(id), fg_color="#333333", hover_color="#5d5e5e", text_color="darkgray", corner_radius=1, font=("Segoe UI Variable Display", 10))
                    delete_button.pack(side="left", padx=(0, 2), pady=5)

                    
                    prioridade_button = ctk.CTkButton(tarefa_frame, anchor ="s", width=25, height=55, hover_color="#5d5e5e", text="AP", 
                                                    command=lambda id=doc.id: definir_alta_prioridade(id), 
                                                    fg_color="#780202" if tarefa_data.get('alta_prioridade', False) else cor_frame, 
                                                    text_color="darkgray", corner_radius=1, font=("Segoe UI Variable Display", 10))
                    prioridade_button.pack(side="right", padx=5, pady=1)
            
            # Atualiza o tamanho do frame interno
            frame_tarefas_usuario_interior.update_idletasks()
            canvas_usuario.config(scrollregion=canvas_usuario.bbox("all"))

        # Criar a interface de gerenciamento para o usuário
        janela_usuario = ctk.CTk()
        janela_usuario.title(f"Adicionar Tarefas para {username}")
        janela_usuario.geometry("600x400")
        janela_usuario.after(250, lambda: janela_usuario.iconbitmap('CDA.ico'))

        frame_entrada_usuario = ctk.CTkFrame(janela_usuario, fg_color="#262626", corner_radius=0)
        frame_entrada_usuario.pack(fill="x", padx=10, pady=10)

        entrada_tarefa_usuario = ctk.CTkTextbox(frame_entrada_usuario, height=10, width=55, fg_color="#333333", text_color="#ffffff", font=("Segoe UI Variable Display", 13))
        entrada_tarefa_usuario.pack(side="left", fill="both", expand=True, padx=5)

        botao_adicionar_usuario = ctk.CTkButton(frame_entrada_usuario, height=50, width=15, text="Adicionar", hover_color="#015e5e", command=adicionar_tarefa_usuario, fg_color="#006666", corner_radius=3)
        botao_adicionar_usuario.pack(side="left", padx=2)

        frame_tarefas_usuario = ctk.CTkFrame(janela_usuario, corner_radius=0)
        frame_tarefas_usuario.pack(fill="both", expand=True, padx=10, pady=10)

        canvas_usuario = ctk.CTkCanvas(frame_tarefas_usuario, bg="#262626", highlightthickness=0)
        canvas_usuario.pack(side="left", fill="both", expand=True)

        scrollbar_usuario = ctk.CTkScrollbar(frame_tarefas_usuario, command=canvas_usuario.yview, orientation="vertical", fg_color="#262626", button_hover_color="#a3a3a3", bg_color="#262626", button_color="#262626")
        scrollbar_usuario.pack(side="right", fill="y")

        canvas_usuario.configure(yscrollcommand=scrollbar_usuario.set)
        canvas_usuario.bind_all("<MouseWheel>", handle_mousewheel)

        frame_tarefas_usuario_interior = ctk.CTkFrame(canvas_usuario, corner_radius=0)
        canvas_usuario.create_window((0, 0), window=frame_tarefas_usuario_interior, anchor="nw")

        atualizar_lista_tarefas_usuario()
        janela_usuario.mainloop()

    # Configurar e exibir a interface de gerenciamento de usuários
    ctk.CTkLabel(janela_admin, text="Gerenciamento de Usuários", font=("Segoe UI Variable Display", 16)).pack(pady=10)
    
    frame_usuarios = ctk.CTkFrame(janela_admin, corner_radius=0)
    frame_usuarios.pack(fill="both", expand=True, padx=10, pady=10)

    canvas_usuarios = ctk.CTkCanvas(frame_usuarios, bg="#262626", highlightthickness=0)
    canvas_usuarios.pack(side="left", fill="both", expand=True)

    scrollbar_usuarios = ctk.CTkScrollbar(frame_usuarios, command=canvas_usuarios.yview, orientation="vertical", fg_color="#262626", bg_color="#262626", button_color="#262626")
    scrollbar_usuarios.pack(side="right", fill="y")

    canvas_usuarios.configure(yscrollcommand=scrollbar_usuarios.set)
    canvas_usuarios.bind_all("<MouseWheel>", handle_mousewheel)

    canvas = ctk.CTkCanvas(frame_usuarios, bg="#262626", highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)

    frame_tarefas_usuario_interior = ctk.CTkFrame(canvas_usuarios, corner_radius=0)
    canvas_usuarios.create_window((0, 0), window=frame_tarefas_usuario_interior, anchor="nw")

    atualizar_lista_usuarios()
    janela_admin.mainloop()

# Função auxiliar para rolagem com a roda do mouse
def handle_mousewheel(event):
    canvas_usuario.yview_scroll(int(-1*(event.delta/120)), "units")


# Função para fechar a aplicação e a conexão com o banco de dados
def on_closing():
    #cursor.close()
    #conn.close()
    janela.destroy()

# Função para ajustar a altura do campo de entrada de texto
def ajustar_altura_texto(event=None):
    linhas = int(entrada_tarefa.index("end-1c").split(".")[0])
    altura = min(5, linhas)
    entrada_tarefa.config(height=altura)

# Função para lidar com o evento de teclado no campo de entrada
def handle_keypress(event=None):
     if event.keysym == "Return":  # Se a tecla "Enter" for pressionada
        if event.state & 0x0001:  # Verifica se "Shift" está pressionado
            # Adiciona uma nova linha somente se o texto atual não terminar com uma quebra de linha
            text_content = entrada_tarefa.get("1.0", "end-1c")  # Obtém o texto sem a nova linha final
            if not text_content.endswith("\n"):
                entrada_tarefa.insert("insert", "\n")  # Adiciona uma nova linha
        else:
            adicionar_tarefa()  # Adiciona a tarefa
            entrada_tarefa.delete("1.0", "end") # Limpa o campo de entrada # Limpa o campo de entrada

    # Ajusta a altura da caixa de texto conforme o texto cresce
     content = entrada_tarefa.get("1.0", "end-1c")
     lines = content.splitlines()
     new_height = max(10, len(lines) * 20)
     entrada_tarefa.configure(height=new_height)

# Função para verificar login
def verificar_login():
    username = entrada_usuario.get()
    password = entrada_senha.get()
    usuarios_ref = db.collection('usuarios').where('username', '==', username).where('password', '==', password).stream()
    user = list(usuarios_ref)

    if user:
        if username == 'admin':
            janela_login.destroy()
            exibir_gerenciamento_admin()
        else:
            if lembrar_usuario_var.get():
                # Armazena nome de usuário e senha (se desejar)
                with open("user_config.txt", "w") as file:
                    file.write(username + '\n' + password)
            else:
                # Remove o arquivo se a opção "Lembrar usuário" não for marcada
                if os.path.exists("user_config.txt"):
                    os.remove("user_config.txt")
            janela_login.destroy()
            iniciar_programa()
    else:
        messagebox.showerror("Erro", "Usuário ou senha inválidos.")



# Função para registrar um novo usuário
def registrar_usuario():
    username = entrada_usuario_reg.get()
    password = entrada_senha_reg.get()
    try:
        usuarios_ref = db.collection('usuarios')
        usuarios_ref.add({
            'username': username,
            'password': password
        })
        messagebox.showinfo("Sucesso", "Usuário cadastrado com sucesso!")
        janela_registro.destroy()
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao registrar usuário: {e}")


# Função para exibir a janela de registro
def exibir_registro():
    global janela_registro, entrada_usuario_reg, entrada_senha_reg

    janela_registro = ctk.CTkToplevel()
    janela_registro.title("Registro de Usuário")
    janela_registro.geometry("350x300")
    janela_registro.after(250, lambda: janela_registro.iconbitmap('CDA.ico'))


    ctk.CTkLabel(janela_registro, text="Digite seus dados para registro", font=("Century Gothic", 16)).pack(pady=10)
    ctk.CTkLabel(janela_registro, text="Nome de Usuário", font=("Segoe UI Variable Display", 13)).pack(pady=5)
    entrada_usuario_reg = ctk.CTkEntry(janela_registro, width=200)
    entrada_usuario_reg.pack()

    ctk.CTkLabel(janela_registro, text="Senha", font=("Segoe UI Variable Display", 13)).pack(pady=5)
    entrada_senha_reg = ctk.CTkEntry(janela_registro, show="*", width=200)
    entrada_senha_reg.pack()

    botao_registrar = ctk.CTkButton(janela_registro, text="Continue", hover_color="#a3a3a3", corner_radius=1, fg_color="#616e81", command=registrar_usuario, font=("Segoe UI Semibold", 14))
    botao_registrar.pack(pady=20)

class CustomScrollbar(ctk.CTkScrollbar):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(button_color="#262626")  # Define a cor do botão

    def set_button_size(self, size):
        """Define o tamanho do botão do scrollbar."""
        self.button_size = size
        self.update_button_size()

    def update_button_size(self):
        """Atualiza o tamanho do botão do scrollbar."""
        self.configure(width=self.button_size)


# Função para iniciar o programa principal após o login
def iniciar_programa():
    global janela, entrada_tarefa, frame_tarefas_usuario_interior, canvas

    janela = ctk.CTk()
    janela.title("Lista de Tarefas")
    janela.iconbitmap("CDA.ico")
    janela.geometry("500x500")

    # Frame para entrada de tarefas
    frame_principal = ctk.CTkFrame(janela, corner_radius=14)
    frame_principal.pack(fill="both", expand=True)

    frame_entrada = ctk.CTkFrame(frame_principal, fg_color="#262626")
    frame_entrada.pack(fill="both", padx=10, pady=10)

    entrada_tarefa = ctk.CTkTextbox(frame_entrada, height=10, width=55, fg_color="#262626", text_color="#ffffff", font=("Segoe UI Variable Display", 15))
    entrada_tarefa.pack(side="left", fill="both", expand=True)
    entrada_tarefa.bind("<KeyRelease>", handle_keypress)

    image_path = "play.png"  # substitua pelo caminho para o seu ícone
    icon_image = Image.open(image_path)
    icon_image = icon_image.resize((30, 30), Image.LANCZOS)  # redimensione conforme necessário
    icon_photo = ImageTk.PhotoImage(icon_image)

    botao_adicionar = ctk.CTkButton(frame_entrada, height=50, width=15, text="", command=adicionar_tarefa, fg_color="#006666", bg_color="#262626", hover_color="#017878", corner_radius=14, border_width=8, border_color="#262626" , image=icon_photo)
    botao_adicionar.pack(side="left", padx=2)

    frame_tarefas = ctk.CTkFrame(frame_principal, corner_radius=0)
    frame_tarefas.pack(fill="both", expand=True, padx=13, pady=10)

    canvas = ctk.CTkCanvas(frame_tarefas, bg="#262626", highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)

# Use o scrollbar personalizado
    scrollbar = CustomScrollbar(frame_tarefas, command=canvas.yview, orientation="vertical", fg_color="#262626", bg_color="#262626")
    scrollbar.set_button_size(13)  # Defina o tamanho desejado para o botão
    scrollbar.pack(side="right", fill="y")

    canvas.configure(yscrollcommand=scrollbar.set)

    frame_tarefas_usuario_interior = ctk.CTkFrame(canvas, corner_radius=0)
    canvas.create_window((0, 0), window=frame_tarefas_usuario_interior, anchor="nw")

    frame_tarefas_usuario_interior.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(-1 * int(event.delta / 120), "units"))

    atualizar_lista_tarefas()
    janela.protocol("WM_DELETE_WINDOW", on_closing)
    janela.mainloop()

# Janela de login
janela_login = ctk.CTk()
janela_login.title("Controle de Atividades")
janela_login.iconbitmap("CDA.ico")
janela_login.geometry("400x350")

ctk.CTkLabel(janela_login, text_color="#ffffff", text="Controle de Atividades", font=("Segoe UI Variable Semibold", 20)).pack(pady=10)

ctk.CTkLabel(janela_login, text="Nome de Usuário", font=("Segoe UI Variable Display", 14)).pack(pady=5)
entrada_usuario = ctk.CTkEntry(janela_login, placeholder_text=("Usuário"), width=200)
entrada_usuario.pack()

ctk.CTkLabel(janela_login, text="Senha", font=("Segoe UI Variable Display", 14)).pack(pady=5)
entrada_senha = ctk.CTkEntry(janela_login, placeholder_text=("Senha"), show="*", width=200)
entrada_senha.pack()

# Checkbox para lembrar usuário
lembrar_usuario_var = tk.BooleanVar()
lembrar_usuario_checkbox = ctk.CTkCheckBox(janela_login, text="Lembrar usuário", corner_radius=1, hover_color="#a3a3a3", fg_color="#008080", font=("Segoe UI Variable Display", 13), variable=lembrar_usuario_var)
lembrar_usuario_checkbox.pack(pady=15)

# Função para carregar as informações do usuário armazenadas
def carregar_usuario_lembrado():
    if os.path.exists("user_config.txt"):
        with open("user_config.txt", "r") as file:
            dados = file.readlines()
            if len(dados) == 2:
                # Preencher os campos com nome de usuário e senha
                entrada_usuario.insert(0, dados[0].strip())
                #entrada_senha.insert(0, dados[1].strip())
                lembrar_usuario_var.set(1)  # Marcar a caixa de lembrar usuário
            else:
                lembrar_usuario_var.set(0)  # Desmarcar a caixa se houver algum problema no arquivo

# Chame a função ao iniciar a tela de login
carregar_usuario_lembrado()


botao_login = ctk.CTkButton(janela_login, text="Login", hover_color="#006161", corner_radius=1, fg_color="#008080", command=verificar_login, font=("Segoe UI Semibold", 14))
botao_login.pack(pady=20)

ctk.CTkButton(janela_login, text="Registrar", hover_color="#006161", corner_radius=1, fg_color="#008080", command=exibir_registro, font=("Segoe UI Semibold", 14)).pack()

janela_login.mainloop()
