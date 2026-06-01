import base64
import html
import mimetypes
import re
import hashlib
import random
import time
from pathlib import Path
from datetime import datetime, date, timedelta

import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client

st.set_page_config(
    page_title="GarageHub - Garagem Hot Wheels",
    page_icon="🏁",
    layout="wide"
)


# =========================
# MOBILE / PWA MODE
# =========================
def ativar_mobile_pwa():
    st.markdown("""
    <link rel="manifest" href="/manifest.json">

    <meta name="theme-color" content="#facc15">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="application-name" content="GarageHub">

    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-title" content="GarageHub">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">

    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">

    <style>
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
            padding-top: 0.75rem !important;
        }

        .hero,
        .pro-hero,
        .profile-banner,
        .market-hero,
        .member-card,
        .qr-card {
            border-radius: 22px !important;
            padding: 18px !important;
        }

        .hero-title,
        .market-title {
            font-size: 30px !important;
        }

        .market-card {
            grid-template-columns: 1fr !important;
            padding: 16px !important;
            border-radius: 24px !important;
        }

        .market-img,
        .market-empty {
            height: 260px !important;
        }

        .market-price-grid,
        .pro-grid,
        .feature-grid {
            grid-template-columns: 1fr !important;
        }

        .stButton > button,
        .stFormSubmitButton > button {
            width: 100% !important;
            min-width: 100% !important;
            min-height: 48px !important;
            border-radius: 16px !important;
        }

        input,
        textarea,
        div[data-baseweb="select"] {
            font-size: 16px !important;
        }

        section[data-testid="stSidebar"] {
            width: 86vw !important;
        }
    }

    .garagehub-install-card {
        background:
            radial-gradient(circle at top left, rgba(250,204,21,.22), transparent 34%),
            linear-gradient(145deg, rgba(15,23,42,.96), rgba(2,6,23,.98));
        border: 1px solid rgba(250,204,21,.32);
        border-radius: 24px;
        padding: 18px;
        margin: 14px 0 22px;
        box-shadow: 0 18px 44px rgba(0,0,0,.30), 0 0 28px rgba(250,204,21,.08);
    }

    .garagehub-install-card h3 {
        margin: 0 0 6px;
        color: #facc15;
    }

    .garagehub-install-card p {
        margin: 0;
        color: #cbd5e1;
        font-weight: 800;
    }


    /* =========================
       ALERTAS FINANCEIROS ADMIN
       ========================= */
    .alerta-financeiro-wrap {
        margin: 14px 0 22px;
    }
    .alerta-financeiro-hero {
        background: linear-gradient(145deg, rgba(15,23,42,.95), rgba(2,6,23,.98));
        border: 1px solid rgba(250,204,21,.26);
        border-radius: 24px;
        padding: 18px;
        box-shadow: 0 18px 44px rgba(0,0,0,.28);
    }
    .alerta-financeiro-hero h3 {
        margin: 0 0 6px;
        color: #f8fafc;
        font-size: 22px;
    }
    .alerta-financeiro-hero p {
        margin: 0;
        color: #cbd5e1;
        font-weight: 800;
    }
    .alerta-financeiro-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 14px;
        margin-top: 14px;
    }
    .alerta-pagamento-amarelo,
    .alerta-pagamento-vermelho {
        border-radius: 22px;
        padding: 16px;
        box-shadow: 0 18px 38px rgba(0,0,0,.28);
    }
    .alerta-pagamento-amarelo {
        background: repeating-linear-gradient(
            45deg,
            rgba(250, 204, 21, .28),
            rgba(250, 204, 21, .28) 10px,
            rgba(113, 63, 18, .18) 10px,
            rgba(113, 63, 18, .18) 20px
        );
        border: 2px solid #facc15;
        color: #fef9c3;
    }
    .alerta-pagamento-vermelho {
        background: repeating-linear-gradient(
            45deg,
            rgba(239, 68, 68, .32),
            rgba(239, 68, 68, .32) 10px,
            rgba(127, 29, 29, .25) 10px,
            rgba(127, 29, 29, .25) 20px
        );
        border: 2px solid #ef4444;
        color: #fee2e2;
    }
    .alerta-pagamento-amarelo h4,
    .alerta-pagamento-vermelho h4 {
        margin: 0 0 8px;
        font-size: 18px;
        color: inherit;
    }
    .alerta-pagamento-amarelo p,
    .alerta-pagamento-vermelho p {
        margin: 4px 0;
        font-weight: 850;
        color: inherit;
    }
    @media (max-width: 900px) {
        .alerta-financeiro-grid { grid-template-columns: 1fr; }
    }
    </style>
    """, unsafe_allow_html=True)


ativar_mobile_pwa()

BASE_DIR = Path(__file__).parent
BANNER_PATH = BASE_DIR / "assets" / "banner.jpg"
STORAGE_BUCKET = "fotos-minis"

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# =========================
# UTILITÁRIOS
# =========================

def limpar_campo_visual(valor, padrao="-"):
    """Limpa valores vindos do banco para exibição segura no app."""
    if valor is None:
        return padrao

    texto = str(valor).strip()

    if not texto or texto.lower() in ["none", "null", "nan"]:
        return padrao

    if any(s in texto.lower() for s in ["<div", "<p", "<span", "class=", "price-row", "mini-meta"]):
        return padrao

    return texto

def img_base64(path):
    path = Path(path)
    if not path.exists():
        return ""
    return base64.b64encode(path.read_bytes()).decode()


def injetar_melhorias_login_browser(lembrar_email=True):
    """
    Melhoria visual/UX da tela de login.
    Não altera autenticação, banco, senha, admin, cliente, loja, pré-venda ou scanner.

    O que faz:
    - tenta colocar o foco no campo de e-mail;
    - ajuda o navegador a reconhecer e-mail/senha para autocomplete;
    - salva SOMENTE o e-mail no localStorage do navegador quando o cliente marcar "lembrar".
    """
    lembrar_js = "true" if lembrar_email else "false"

    components.html(f"""
    <script>
    (function() {{
        const lembrar = {lembrar_js};
        const STORAGE_KEY = "garagehub_login_email";

        function acharInputPorLabel(textoLabel) {{
            const labels = Array.from(window.parent.document.querySelectorAll("label"));
            const label = labels.find(l => (l.innerText || "").trim().toLowerCase().includes(textoLabel));
            if (!label) return null;

            const forId = label.getAttribute("for");
            if (forId) {{
                const byFor = window.parent.document.getElementById(forId);
                if (byFor) return byFor;
            }}

            const bloco = label.closest("div");
            if (bloco) {{
                const input = bloco.querySelector("input");
                if (input) return input;
            }}

            return null;
        }}

        function aplicar() {{
            const emailInput =
                acharInputPorLabel("e-mail") ||
                window.parent.document.querySelector('input[aria-label="E-mail"]') ||
                window.parent.document.querySelector('input[type="text"]');

            const senhaInput =
                acharInputPorLabel("senha") ||
                window.parent.document.querySelector('input[type="password"]');

            if (emailInput) {{
                emailInput.setAttribute("autocomplete", "email");
                emailInput.setAttribute("name", "email");
                emailInput.setAttribute("id", "garagehub-login-email");
                emailInput.setAttribute("inputmode", "email");

                const salvo = window.parent.localStorage.getItem(STORAGE_KEY);
                if (lembrar && salvo && !emailInput.value) {{
                    emailInput.value = salvo;
                    emailInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                    emailInput.dispatchEvent(new Event("change", {{ bubbles: true }}));
                }}

                emailInput.addEventListener("input", function() {{
                    if (lembrar) {{
                        window.parent.localStorage.setItem(STORAGE_KEY, emailInput.value || "");
                    }}
                }});

                setTimeout(function() {{
                    try {{
                        if (!emailInput.value) emailInput.focus();
                    }} catch (e) {{}}
                }}, 250);
            }}

            if (senhaInput) {{
                senhaInput.setAttribute("autocomplete", "current-password");
                senhaInput.setAttribute("name", "password");
                senhaInput.setAttribute("id", "garagehub-login-password");
            }}

            if (!lembrar) {{
                window.parent.localStorage.removeItem(STORAGE_KEY);
            }}
        }}

        setTimeout(aplicar, 250);
        setTimeout(aplicar, 900);
        setTimeout(aplicar, 1800);
    }})();
    </script>
    """, height=0)


def money(valor):
    try:
        return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"




def pix_chave_padrao():
    """Chave Pix configurável via Streamlit Secrets. Se não existir, usa placeholder seguro."""
    try:
        return st.secrets.get("PIX_CHAVE", "configure-sua-chave-pix")
    except Exception:
        return "configure-sua-chave-pix"


def pix_nome_recebedor():
    try:
        return st.secrets.get("PIX_RECEBEDOR", "GARAGEHUB")
    except Exception:
        return "GARAGEHUB"


def gerar_pix_copia_cola(pedido):
    """Gera um código Pix interno para fluxo assistido/manual."""
    valor = float(pedido.get("valor") or 0)
    pedido_id = str(pedido.get("id") or "0")
    usuario_id = str(pedido.get("usuario_id") or "0")
    base = f"GHW|PEDIDO:{pedido_id}|CLIENTE:{usuario_id}|VALOR:{valor:.2f}|CHAVE:{pix_chave_padrao()}"
    token = hashlib.sha256(base.encode("utf-8")).hexdigest()[:12].upper()
    return f"PIX-GARAGEHUB-{pedido_id}-{token}-R${valor:.2f}-CHAVE:{pix_chave_padrao()}"


def pix_card_html(pedido, titulo="Pagamento Pix"):
    codigo = html.escape(gerar_pix_copia_cola(pedido))
    valor = money(pedido.get("valor") or 0)
    recebedor = html.escape(pix_nome_recebedor())
    titulo_safe = html.escape(titulo)
    return f"""
    <div class="pix-card">
        <div class="pix-head">
            <div>
                <div class="pix-kicker">💳 Pix assistido</div>
                <h3>{titulo_safe}</h3>
                <p>Valor: <b>{valor}</b> • Recebedor: <b>{recebedor}</b></p>
            </div>
            <div class="pix-fake-qr"></div>
        </div>
        <div class="pix-code"><code>{codigo}</code></div>
        <p class="pix-help">Copie o código, pague pelo app do banco e avise o admin. O admin confirma e lança a mini na garagem.</p>
    </div>
    """

def slugify(texto):
    texto = str(texto or "arquivo").lower().strip()
    texto = re.sub(r"[^a-z0-9áàâãéèêíïóôõöúçñ_-]+", "-", texto)
    texto = texto.replace("ç", "c").replace("ã", "a").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    texto = re.sub(r"-+", "-", texto).strip("-")
    return texto or "arquivo"


def is_url(valor):
    valor = str(valor or "")
    return valor.startswith("http://") or valor.startswith("https://")


def is_data_image(valor):
    valor = str(valor or "")
    return valor.startswith("data:image/")


def normalizar_url_imagem(valor):
    """Normaliza URLs/caminhos de foto vindos da Base44, Supabase ou upload local."""
    if not valor:
        return ""

    valor = html.unescape(str(valor)).strip()

    # Evita que HTML quebrado salvo por engano vire src de imagem.
    if any(s in valor.lower() for s in ["<div", "<p", "<span", "class=", "mini-meta", "price-row"]):
        return ""

    # Alguns exports podem vir com aspas ou espaços.
    valor = valor.strip("'").strip('"').strip()
    valor = valor.replace(" ", "%20")

    return valor



def get_foto_perfil_usuario(usuario):
    """Foto de perfil de usuário/admin. Prioriza foto_perfil_url antes de qualquer outro campo."""
    if not usuario:
        return ""

    for campo in [
        "foto_perfil_url",
        "perfil_url",
        "avatar_url",
        "foto_url",
        "foto",
        "imagem",
        "image_url",
        "url_foto",
    ]:
        valor = usuario.get(campo)
        valor = normalizar_url_imagem(valor)
        if valor:
            return valor

    return ""


def get_foto_item(item):
    """Busca foto em vários nomes de coluna para manter compatibilidade com Base44/Supabase/app."""
    if not item:
        return ""

    for campo in [
        "foto_url",
        "foto",
        "imagem",
        "image",
        "image_url",
        "img",
        "thumbnail",
        "url_foto",
        "comprovante_url",
        "foto_perfil_url",
    ]:
        valor = item.get(campo)
        valor = normalizar_url_imagem(valor)
        if valor:
            return valor

    return ""


def foto_src(foto):
    """Aceita URL pública ou caminho local e devolve um src pronto para HTML/Streamlit."""
    foto = normalizar_url_imagem(foto)
    if not foto:
        return ""

    if is_data_image(foto) or is_url(foto):
        return foto

    p = Path(foto)
    if p.exists():
        ext = p.suffix.lower().replace(".", "") or "jpeg"
        mime = "jpeg" if ext in ["jpg", "jpeg"] else "png"
        return f"data:image/{mime};base64,{img_base64(p)}"

    return ""


def imagem_html(foto, classe="mini-img"):
    src = foto_src(foto)
    if src:
        src_safe = html.escape(src, quote=True)
        classe_safe = html.escape(classe, quote=True)
        return f'<img src="{src_safe}" class="{classe_safe}" loading="lazy" referrerpolicy="no-referrer">'
    return '<div class="mini-img empty-img">🏎️</div>'


def perfil_html(foto, inicial="👤"):
    """Renderiza avatar circular. Aceita URL pública, data:image/base64 ou arquivo local existente."""
    src = foto_src(foto)
    inicial = html.escape(str(inicial or "👤")[:1].upper())

    if src:
        src_safe = html.escape(src, quote=True)
        return f"""
        <div class="perfil-avatar-safe">
            <img src="{src_safe}" loading="lazy" referrerpolicy="no-referrer" alt="Foto de perfil">
        </div>
        """

    return f"""
    <div class="perfil-avatar-safe perfil-avatar-empty">
        {inicial}
    </div>
    """


def upload_storage(uploaded_file, pasta, prefixo):
    """
    Upload de imagem blindado para o GarageHub.

    Fluxo correto:
    1) tenta salvar no Supabase Storage e retorna URL pública;
    2) se o Storage falhar, NÃO salva caminho local /mount/src;
    3) usa data:image base64 como fallback para a foto continuar aparecendo
       mesmo quando o cadastro é feito por outra pessoa/casa/dispositivo.
    """
    if uploaded_file is None:
        return ""

    extensao = uploaded_file.name.split(".")[-1].lower()
    mime = mimetypes.guess_type(uploaded_file.name)[0] or "image/jpeg"
    nome = f"{pasta}/{slugify(prefixo)}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.{extensao}"
    dados = uploaded_file.getvalue()

    try:
        supabase.storage.from_(STORAGE_BUCKET).upload(
            nome,
            dados,
            file_options={"content-type": mime, "upsert": "true"}
        )
        url_publica = supabase.storage.from_(STORAGE_BUCKET).get_public_url(nome)
        if url_publica:
            return str(url_publica)
    except Exception:
        pass

    # Fallback seguro: nunca grava caminho local no banco.
    b64 = base64.b64encode(dados).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def upload_storage_loja(uploaded_file, prefixo):
    """Upload EXCLUSIVO para fotos da Loja.

    Diferente do upload geral, aqui NÃO existe fallback em base64.
    Motivo: base64 dentro de loja_minis.foto_url deixa a tabela pesada e causa timeout.
    A foto continua em qualidade original no Supabase Storage e o banco guarda só a URL pública.
    """
    if uploaded_file is None:
        return ""

    extensao = uploaded_file.name.split(".")[-1].lower()
    mime = mimetypes.guess_type(uploaded_file.name)[0] or "image/jpeg"
    nome = f"loja/{slugify(prefixo)}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.{extensao}"
    dados = uploaded_file.getvalue()

    try:
        supabase.storage.from_(STORAGE_BUCKET).upload(
            nome,
            dados,
            file_options={"content-type": mime, "upsert": "true"}
        )
        url_publica = supabase.storage.from_(STORAGE_BUCKET).get_public_url(nome)
        if url_publica and str(url_publica).startswith("http"):
            return str(url_publica)
    except Exception as e:
        raise Exception(
            "Falha ao enviar a foto da Loja para o Supabase Storage. "
            "Verifique se o bucket 'fotos-minis' existe e está público. "
            f"Erro real: {e}"
        )

    raise Exception("Não foi possível obter URL pública da foto enviada para o Storage.")


def upload_perfil_avatar(uploaded_file, pasta="perfis", prefixo="avatar"):
    """
    Upload blindado para foto de perfil.
    Primeiro tenta Supabase Storage. Se o bucket/permissão falhar, grava a imagem
    como data:image base64 no próprio campo do usuário para o avatar aparecer sempre.
    """
    if uploaded_file is None:
        return ""

    mime = mimetypes.guess_type(uploaded_file.name)[0] or "image/jpeg"
    dados = uploaded_file.getvalue()

    try:
        extensao = uploaded_file.name.split(".")[-1].lower()
        nome = f"{pasta}/{slugify(prefixo)}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.{extensao}"

        supabase.storage.from_(STORAGE_BUCKET).upload(
            nome,
            dados,
            file_options={"content-type": mime, "upsert": "true"}
        )

        url_publica = supabase.storage.from_(STORAGE_BUCKET).get_public_url(nome)
        if url_publica:
            return str(url_publica)

    except Exception:
        pass

    b64 = base64.b64encode(dados).decode("utf-8")
    return f"data:{mime};base64,{b64}"


# =========================
# BANCO / SUPABASE
# =========================
def login(email, senha):
    usuario = buscar_usuario_por_email(email)

    if not usuario:
        return None

    senha_salva = str(usuario.get("senha") or "")

    if senha_salva == senha:
        return usuario

    return None



def buscar_usuario_por_email(email):
    try:
        resp = (
            supabase.table("usuarios")
            .select("*")
            .eq("email", email.strip().lower())
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception:
        return None




def buscar_usuario_por_id(usuario_id):
    try:
        resp = (
            supabase.table("usuarios")
            .select("*")
            .eq("id", usuario_id)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception:
        return None


def senha_pendente(usuario):
    senha = str(usuario.get("senha") or "").strip().lower()

    return (
        senha == ""
        or senha in [
            "pendente",
            "123456",
            "12345",
            "1234",
            "trocar",
            "primeiro_acesso",
            "primeiro acesso",
            "senha_pendente",
            "null",
            "none"
        ]
    )


def definir_nova_senha(usuario_id, nova_senha):
    supabase.table("usuarios").update({
        "senha": nova_senha
    }).eq("id", usuario_id).execute()



def atualizar_foto_perfil(usuario_id, foto_url):
    foto_url = foto_url or ""

    try:
        supabase.table("usuarios").update({
            "foto_perfil_url": foto_url,
            "foto_url": foto_url
        }).eq("id", usuario_id).execute()
        return True
    except Exception:
        pass

    try:
        supabase.table("usuarios").update({
            "foto_perfil_url": foto_url
        }).eq("id", usuario_id).execute()
        return True
    except Exception:
        pass

    supabase.table("usuarios").update({
        "foto_url": foto_url
    }).eq("id", usuario_id).execute()
    return True

def atualizar_email_cliente(usuario_id, novo_email):
    supabase.table("usuarios").update({
        "email": novo_email.strip().lower()
    }).eq("id", usuario_id).execute()


def resetar_senha_cliente(usuario_id):
    supabase.table("usuarios").update({
        "senha": "primeiro_acesso"
    }).eq("id", usuario_id).execute()



def status_mini(mini):
    return str(mini.get("status_pagamento") or "").strip().lower()


def is_pendente_pagamento(mini):
    return status_mini(mini) in ["pendente", "solicitado", "aguardando_pix", "reservado"]


def total_pendente_pagamento(minis):
    return sum(
        float(m.get("valor_pago") or 0)
        for m in (minis or [])
        if is_pendente_pagamento(m)
    )


def qtd_pendente_pagamento(minis):
    return len([m for m in (minis or []) if is_pendente_pagamento(m)])



def normalizar_data_pagamento_prevista(valor):
    """Converte data prevista de pagamento para date, aceitando date/datetime/texto."""
    if not valor:
        return None

    if isinstance(valor, datetime):
        return valor.date()

    if isinstance(valor, date):
        return valor

    texto = str(valor).strip()
    if not texto or texto.lower() in ["none", "null", "nan"]:
        return None

    try:
        return datetime.fromisoformat(texto[:10]).date()
    except Exception:
        pass

    for formato in ["%d/%m/%Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(texto[:10], formato).date()
        except Exception:
            pass

    return None


def classificar_alerta_pagamento(data_prevista, status_pagamento):
    """Retorna vencido, vence_hoje, vence_amanha, futuro ou vazio. Não altera banco."""
    status = str(status_pagamento or "").strip().lower()
    if status in ["pago", "concluido", "cancelado", "incluido_na_garagem"]:
        return ""

    data_venc = normalizar_data_pagamento_prevista(data_prevista)
    if not data_venc:
        return ""

    hoje = date.today()
    if data_venc < hoje:
        return "vencido"
    if data_venc == hoje:
        return "vence_hoje"
    if data_venc == hoje + timedelta(days=1):
        return "vence_amanha"
    return "futuro"


def formatar_data_br(valor):
    data_venc = normalizar_data_pagamento_prevista(valor)
    return data_venc.strftime("%d/%m/%Y") if data_venc else "-"


def montar_alertas_financeiros_admin(minis, clientes):
    """Monta alertas de leitura para o admin com base em data_pagamento_prevista da tabela minis."""
    clientes_por_id = {str(c.get("id")): c for c in (clientes or [])}
    alertas = []

    for mini in minis or []:
        tipo_alerta = classificar_alerta_pagamento(
            mini.get("data_pagamento_prevista"),
            mini.get("status_pagamento")
        )
        if tipo_alerta not in ["vencido", "vence_hoje", "vence_amanha"]:
            continue

        cliente = clientes_por_id.get(str(mini.get("usuario_id")), {})
        data_venc = normalizar_data_pagamento_prevista(mini.get("data_pagamento_prevista"))
        dias_atraso = 0
        if data_venc and tipo_alerta == "vencido":
            dias_atraso = max(0, (date.today() - data_venc).days)

        alertas.append({
            "tipo": tipo_alerta,
            "cliente": cliente,
            "mini": mini,
            "data": data_venc,
            "dias_atraso": dias_atraso,
        })

    return sorted(alertas, key=lambda a: (a.get("data") or date.max, str(a.get("cliente", {}).get("nome") or "")))


def render_alertas_financeiros_admin(minis, clientes, limite=12):
    alertas = montar_alertas_financeiros_admin(minis, clientes)
    vencidos = [a for a in alertas if a["tipo"] == "vencido"]
    vence_hoje = [a for a in alertas if a["tipo"] == "vence_hoje"]
    vence_amanha = [a for a in alertas if a["tipo"] == "vence_amanha"]

    total_urgentes = len(vencidos) + len(vence_hoje) + len(vence_amanha)

    st.markdown(f"""
    <div class="alerta-financeiro-wrap">
        <div class="alerta-financeiro-hero">
            <h3>🔔 Alertas financeiros do admin</h3>
            <p>Somente o admin visualiza. Leitura automática de pagamentos pré-datados: {len(vence_amanha)} vence(m) amanhã, {len(vence_hoje)} vence(m) hoje e {len(vencidos)} vencido(s).</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if total_urgentes == 0:
        st.info("Nenhum pagamento pré-datado vencendo amanhã, hoje ou vencido.")
        return

    cards = []
    for alerta in (vencidos + vence_hoje + vence_amanha)[:limite]:
        mini = alerta.get("mini") or {}
        cliente = alerta.get("cliente") or {}
        tipo = alerta.get("tipo")
        classe = "alerta-pagamento-vermelho" if tipo == "vencido" else "alerta-pagamento-amarelo"
        if tipo == "vencido":
            titulo = "🚨 Pagamento vencido"
            extra = f"{alerta.get('dias_atraso', 0)} dia(s) em atraso"
        elif tipo == "vence_hoje":
            titulo = "⚠️ Pagamento vence hoje"
            extra = "vence hoje"
        else:
            titulo = "⚠️ Pagamento vence amanhã"
            extra = "vence amanhã"

        cards.append(f"""
        <div class="{classe}">
            <h4>{html.escape(titulo)}</h4>
            <p><b>Cliente:</b> {html.escape(str(cliente.get('nome') or 'Cliente não identificado'))}</p>
            <p><b>Mini:</b> {html.escape(str(mini.get('nome') or 'Mini'))}</p>
            <p><b>Valor:</b> {money(mini.get('valor_pago') or 0)} • <b>Vencimento:</b> {formatar_data_br(mini.get('data_pagamento_prevista'))}</p>
            <p><b>Status atual:</b> {html.escape(str(mini.get('status_pagamento') or 'pendente'))} • {html.escape(extra)}</p>
        </div>
        """)

    st.markdown('<div class="alerta-financeiro-grid">' + ''.join(cards) + '</div>', unsafe_allow_html=True)



def buscar_minis(usuario_id):
    return (
        supabase.table("minis")
        .select("*")
        .eq("usuario_id", usuario_id)
        .order("criado_em", desc=True)
        .execute()
        .data
    )


def cadastrar_mini(usuario_id, nome, marca, serie, ano, raridade, valor_pago, valor_estimado, foto_url,
                   status_pagamento="pendente", tipo_mini="compra", destaque_cliente="", data_pagamento_prevista=None):
    dados = {
        "usuario_id": usuario_id,
        "nome": nome,
        "marca": marca,
        "serie": serie,
        "ano": ano,
        "raridade": raridade,
        "valor_pago": valor_pago,
        "valor_estimado": valor_estimado,
        "foto_url": foto_url or "",
        "status_pagamento": status_pagamento or "pendente",
        "tipo_mini": tipo_mini or "compra",
        "destaque_cliente": destaque_cliente or "",
        "data_pagamento_prevista": str(data_pagamento_prevista) if data_pagamento_prevista else None
    }

    try:
        supabase.table("minis").insert(dados).execute()
    except Exception:
        # Fallback para ambientes onde as novas colunas ainda não existem.
        dados.pop("status_pagamento", None)
        dados.pop("tipo_mini", None)
        dados.pop("destaque_cliente", None)
        dados.pop("data_pagamento_prevista", None)
        supabase.table("minis").insert(dados).execute()


def buscar_todas_minis():
    return supabase.table("minis").select("*").order("criado_em", desc=True).execute().data


def atualizar_mini(mini_id, dados):
    supabase.table("minis").update(dados).eq("id", mini_id).execute()


def excluir_mini(mini_id):
    supabase.table("minis").delete().eq("id", mini_id).execute()


def origem_operacional_mini(mini):
    """Define a origem operacional sem exigir coluna nova no Supabase.

    Regra de emergência:
    - tipo_mini = loja/compra/pre_venda => protegido, não exclui pela garagem;
    - tipo_mini = manual_migracao/manual/migracao => pode excluir pela garagem do cliente.
    """
    tipo = str((mini or {}).get("tipo_mini") or "").strip().lower()
    destaque = str((mini or {}).get("destaque_cliente") or "").strip().lower()

    if tipo in ["manual_migracao", "manual", "migracao", "migração"]:
        return "manual"

    if "origem: manual" in destaque or "migração" in destaque or "migracao" in destaque:
        return "manual"

    return "loja"


def pode_excluir_mini_pela_garagem(mini):
    return origem_operacional_mini(mini) == "manual"


def buscar_loja_minis(apenas_disponiveis=False):
    """Busca os itens da Loja com retentativa para erro intermitente de cache do Supabase/PostgREST.

    Importante: não transforma todo erro em "tabela não existe".
    Se der erro, a tela mostra o erro real para facilitar o diagnóstico.
    """
    ultimo_erro = None

    for tentativa in range(3):
        try:
            # Busca leve com foto_url.
            # As fotos antigas em base64 já foram migradas para o Supabase Storage,
            # então foto_url agora contém apenas URL pública leve.
            query = supabase.table("loja_minis").select(
                "id,nome,marca,serie,ano,raridade,valor,valor_estimado,foto_url,status,destaque,criado_em"
            )

            if apenas_disponiveis:
                query = query.eq("status", "disponivel")

            resultado = query.order("criado_em", desc=True).execute()
            return resultado.data or []

        except Exception as e:
            ultimo_erro = e
            erro_txt = str(e).lower()

            # Erro intermitente conhecido do Supabase/PostgREST logo após alterações de tabela/deploy.
            if ("pgrst205" in erro_txt or "schema cache" in erro_txt or "could not find the table" in erro_txt) and tentativa < 2:
                time.sleep(0.8)
                continue

            raise

    raise ultimo_erro


def cadastrar_loja_mini(nome, marca, serie, ano, raridade, valor, valor_estimado, foto_url, status, destaque):
    supabase.table("loja_minis").insert({
        "nome": nome,
        "marca": marca,
        "serie": serie,
        "ano": ano,
        "raridade": raridade,
        "valor": valor,
        "valor_estimado": valor_estimado,
        "foto_url": foto_url or "",
        "status": status or "disponivel",
        "destaque": destaque or ""
    }).execute()


def atualizar_loja_mini(loja_id, dados):
    supabase.table("loja_minis").update(dados).eq("id", loja_id).execute()


def excluir_loja_mini(loja_id):
    supabase.table("loja_minis").delete().eq("id", loja_id).execute()


# =========================
# PRÉ-VENDA — MÓDULO ISOLADO DA LOJA
# =========================
def buscar_pre_vendas(apenas_ativas=False):
    query = supabase.table("pre_vendas").select("*")
    if apenas_ativas:
        query = query.in_("status", ["ativa", "esgotada"])
    return query.order("criado_em", desc=True).execute().data or []


def buscar_pre_venda_por_id(pre_venda_id):
    if not pre_venda_id:
        return None
    resp = supabase.table("pre_vendas").select("*").eq("id", pre_venda_id).execute()
    return resp.data[0] if resp.data else None


def cadastrar_pre_venda(nome, marca, serie, escala, foto_url, quantidade_total, valor_total, valor_sinal, data_prevista, observacao):
    supabase.table("pre_vendas").insert({
        "nome": nome,
        "marca": marca,
        "serie": serie,
        "escala": escala,
        "foto_url": foto_url or "",
        "quantidade_total": int(quantidade_total or 0),
        "valor_total": float(valor_total or 0),
        "valor_sinal": float(valor_sinal or 0),
        "data_prevista": data_prevista or "",
        "observacao": observacao or "",
        "status": "ativa"
    }).execute()


def atualizar_pre_venda(pre_venda_id, dados):
    supabase.table("pre_vendas").update(dados).eq("id", pre_venda_id).execute()


def excluir_pre_venda(pre_venda_id):
    supabase.table("pre_vendas").delete().eq("id", pre_venda_id).execute()


def buscar_reservas_pre_venda(pre_venda_id=None, cliente_id=None):
    query = supabase.table("pre_venda_reservas").select("*")
    if pre_venda_id:
        query = query.eq("pre_venda_id", pre_venda_id)
    if cliente_id:
        query = query.eq("cliente_id", cliente_id)
    return query.order("criado_em", desc=True).execute().data or []


def quantidade_reservada_pre_venda(pre_venda_id):
    reservas = buscar_reservas_pre_venda(pre_venda_id=pre_venda_id)
    total = 0
    for r in reservas:
        if str(r.get("status") or "").lower() != "cancelado":
            try:
                total += int(r.get("quantidade") or 0)
            except Exception:
                pass
    return total


def quantidade_restante_pre_venda(pre_venda):
    total = int(pre_venda.get("quantidade_total") or 0)
    reservado = quantidade_reservada_pre_venda(pre_venda.get("id"))
    return max(0, total - reservado)


def criar_reserva_pre_venda(pre_venda, cliente_id, quantidade):
    quantidade = max(1, int(quantidade or 1))
    restante = quantidade_restante_pre_venda(pre_venda)

    if quantidade > restante:
        return False, f"Quantidade indisponível. Restam apenas {restante} unidade(s)."

    valor_total_unit = float(pre_venda.get("valor_total") or 0)
    valor_sinal_unit = float(pre_venda.get("valor_sinal") or 0)

    dados = {
        "pre_venda_id": pre_venda.get("id"),
        "cliente_id": cliente_id,
        "quantidade": quantidade,
        "valor_total": valor_total_unit * quantidade,
        "valor_sinal": valor_sinal_unit * quantidade,
        "valor_restante": max(0, (valor_total_unit - valor_sinal_unit) * quantidade),
        "status": "aguardando_sinal"
    }

    supabase.table("pre_venda_reservas").insert(dados).execute()

    restante_depois = quantidade_restante_pre_venda(pre_venda)
    if restante_depois <= 0:
        atualizar_pre_venda(pre_venda.get("id"), {"status": "esgotada"})

    return True, "Reserva criada com sucesso. Aguarde o admin confirmar o sinal/pagamento."


def atualizar_reserva_pre_venda(reserva_id, dados):
    supabase.table("pre_venda_reservas").update(dados).eq("id", reserva_id).execute()


def efetivar_reserva_pre_venda_na_garagem(reserva, pre_venda):
    if not reserva or not pre_venda:
        return False, "Reserva ou pré-venda inválida."

    if str(reserva.get("status") or "").lower() == "incluido_na_garagem":
        return False, "Esta reserva já foi incluída na garagem."

    qtd = int(reserva.get("quantidade") or 1)
    cliente_id = reserva.get("cliente_id")

    if not cliente_id:
        return False, "Reserva sem cliente vinculado."

    for _ in range(qtd):
        cadastrar_mini(
            cliente_id,
            pre_venda.get("nome") or "Mini pré-venda",
            pre_venda.get("marca") or "Hot Wheels",
            pre_venda.get("serie") or "",
            "",
            "Comum",
            float(pre_venda.get("valor_total") or 0),
            float(pre_venda.get("valor_total") or 0),
            pre_venda.get("foto_url") or "",
            "pago",
            "pre_venda",
            "Incluído a partir de pré-venda GarageHub"
        )

    atualizar_reserva_pre_venda(reserva.get("id"), {"status": "incluido_na_garagem"})
    return True, f"{qtd} mini(s) incluída(s) na garagem do cliente."


def texto_status_pre_venda(status):
    mapa = {
        "ativa": "Ativa",
        "esgotada": "Esgotada",
        "finalizada": "Finalizada",
        "cancelada": "Cancelada",
    }
    return mapa.get(str(status or "").lower(), str(status or "-").title())


def texto_status_reserva(status):
    mapa = {
        "aguardando_sinal": "Aguardando sinal",
        "sinal_pago": "Sinal pago",
        "pago_total": "Pago total",
        "incluido_na_garagem": "Incluído na garagem",
        "cancelado": "Cancelado",
    }
    return mapa.get(str(status or "").lower(), str(status or "-").title())


def render_pre_vendas_admin(clientes):
    st.markdown("""
    <div class="admin-work-card">
        <h3>🚧 Pré-venda avulsa</h3>
        <p>Módulo separado da Loja. Crie cards esporádicos, controle reservas, sinal, pagamento total e inclusão na garagem do cliente.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("➕ Criar nova pré-venda", expanded=False):
        with st.form("form_criar_pre_venda"):
            c1, c2 = st.columns(2)
            with c1:
                nome = st.text_input("Nome da mini")
                marca = st.text_input("Marca", value="Hot Wheels")
                serie = st.text_input("Série / linha")
                escala = st.text_input("Escala", value="1:64")
                foto = st.file_uploader("Foto da pré-venda", type=["jpg", "jpeg", "png"])
            with c2:
                quantidade_total = st.number_input("Quantidade total disponível", min_value=0, step=1, value=1)
                valor_total = st.number_input("Valor total unitário", min_value=0.0, step=1.0)
                valor_sinal = st.number_input("Valor do sinal unitário", min_value=0.0, step=1.0)
                data_prevista = st.text_input("Data prevista", placeholder="Ex: 30/08/2026")
                observacao = st.text_area("Observação", placeholder="Ex: sinal para garantir reserva; restante na entrega.")

            if st.form_submit_button("🚀 Publicar pré-venda"):
                if not nome:
                    st.error("Informe o nome da mini.")
                elif float(valor_sinal or 0) > float(valor_total or 0):
                    st.error("O valor do sinal não pode ser maior que o valor total.")
                else:
                    foto_url = upload_storage(foto, "pre-vendas", nome) if foto is not None else ""
                    cadastrar_pre_venda(nome, marca, serie, escala, foto_url, quantidade_total, valor_total, valor_sinal, data_prevista, observacao)
                    st.success("Pré-venda criada com sucesso.")
                    st.rerun()

    col_refresh_1, col_refresh_2 = st.columns([1, 4])
    with col_refresh_1:
        if st.button("🔄 Atualizar reservas", use_container_width=True, key="admin_refresh_pre_venda_reservas"):
            st.rerun()
    with col_refresh_2:
        st.caption("Atualiza pré-vendas e reservas feitas pelos clientes, sem precisar apertar F5 no navegador.")

    try:
        pre_vendas = buscar_pre_vendas(apenas_ativas=False)
    except Exception as e:
        st.error(f"Não consegui carregar pré-vendas. Confira se as tabelas pre_vendas e pre_venda_reservas existem. Erro: {e}")
        return

    try:
        reservas = buscar_reservas_pre_venda()
    except Exception:
        reservas = []

    clientes_por_id = {str(c.get("id")): c for c in (clientes or [])}

    st.subheader("Pré-vendas cadastradas")
    if not pre_vendas:
        st.info("Nenhuma pré-venda cadastrada ainda.")
    else:
        for pv in pre_vendas:
            pv_id = pv.get("id")
            reservado = quantidade_reservada_pre_venda(pv_id)
            restante = quantidade_restante_pre_venda(pv)
            valor_restante = max(0, float(pv.get("valor_total") or 0) - float(pv.get("valor_sinal") or 0))
            status = str(pv.get("status") or "ativa").lower()
            foto_html = imagem_html(get_foto_item(pv), "market-img") if get_foto_item(pv) else '<div class="market-empty">🏎️</div>'
            status_label_card = "ESGOTADO" if restante <= 0 or status == "esgotada" else texto_status_pre_venda(status)

            st.markdown(f"""
            <div class="market-card">
                {foto_html}
                <div class="market-body">
                    <div class="market-tags">
                        <span class="market-tag market-tag-gold">PRÉ-VENDA</span>
                        <span class="market-tag {'market-tag-sold' if restante <= 0 or status == 'esgotada' else 'market-tag-ok'}">{html.escape(status_label_card)}</span>
                    </div>
                    <h3 class="market-name">{html.escape(str(pv.get('nome') or 'Mini'))}</h3>
                    <p class="market-line"><b>Marca:</b> {html.escape(str(pv.get('marca') or '-'))} • <b>Série:</b> {html.escape(str(pv.get('serie') or '-'))}</p>
                    <p class="market-line"><b>Previsão:</b> {html.escape(str(pv.get('data_prevista') or '-'))}</p>
                    <p class="market-line"><b>Obs:</b> {html.escape(str(pv.get('observacao') or '-'))}</p>
                    <div class="market-price-grid">
                        <div class="market-price"><small>Valor total</small><strong>{money(pv.get('valor_total') or 0)}</strong></div>
                        <div class="market-price"><small>Sinal</small><strong>{money(pv.get('valor_sinal') or 0)}</strong></div>
                        <div class="market-price"><small>Restante</small><strong>{money(valor_restante)}</strong></div>
                        <div class="market-price"><small>Reservas</small><strong>{reservado}/{int(pv.get('quantidade_total') or 0)}</strong></div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"⚙️ Gerenciar pré-venda — {pv.get('nome')}", expanded=False):
                e1, e2, e3 = st.columns(3)
                with e1:
                    novo_qtd = st.number_input("Quantidade total", min_value=0, step=1, value=int(pv.get("quantidade_total") or 0), key=f"pv_qtd_{pv_id}")
                    novo_status = st.selectbox("Status", ["ativa", "esgotada", "finalizada", "cancelada"], index=["ativa", "esgotada", "finalizada", "cancelada"].index(status) if status in ["ativa", "esgotada", "finalizada", "cancelada"] else 0, key=f"pv_status_{pv_id}")
                with e2:
                    novo_valor_total = st.number_input("Valor total unitário", min_value=0.0, step=1.0, value=float(pv.get("valor_total") or 0), key=f"pv_valor_{pv_id}")
                    novo_valor_sinal = st.number_input("Sinal unitário", min_value=0.0, step=1.0, value=float(pv.get("valor_sinal") or 0), key=f"pv_sinal_{pv_id}")
                with e3:
                    nova_previsao = st.text_input("Data prevista", value=str(pv.get("data_prevista") or ""), key=f"pv_prev_{pv_id}")
                    nova_obs = st.text_input("Observação", value=str(pv.get("observacao") or ""), key=f"pv_obs_{pv_id}")

                b1, b2, b3 = st.columns(3)
                with b1:
                    if st.button("💾 Salvar pré-venda", key=f"salvar_pv_{pv_id}", use_container_width=True):
                        if float(novo_valor_sinal or 0) > float(novo_valor_total or 0):
                            st.error("O sinal não pode ser maior que o valor total.")
                        else:
                            status_final = "esgotada" if int(novo_qtd or 0) <= reservado else novo_status
                            atualizar_pre_venda(pv_id, {
                                "quantidade_total": int(novo_qtd or 0),
                                "valor_total": float(novo_valor_total or 0),
                                "valor_sinal": float(novo_valor_sinal or 0),
                                "data_prevista": nova_previsao,
                                "observacao": nova_obs,
                                "status": status_final,
                            })
                            st.success("Pré-venda atualizada.")
                            st.rerun()
                with b2:
                    if st.button("🏁 Finalizar", key=f"finalizar_pv_{pv_id}", use_container_width=True):
                        atualizar_pre_venda(pv_id, {"status": "finalizada"})
                        st.success("Pré-venda finalizada.")
                        st.rerun()
                with b3:
                    confirmar = st.checkbox("Confirmar exclusão", key=f"conf_excluir_pv_{pv_id}")
                    if st.button("🗑️ Excluir", key=f"excluir_pv_{pv_id}", use_container_width=True):
                        if confirmar:
                            excluir_pre_venda(pv_id)
                            st.success("Pré-venda excluída.")
                            st.rerun()
                        else:
                            st.warning("Marque confirmar exclusão.")

    st.divider()
    st.subheader("Reservas de pré-venda")

    if not reservas:
        st.info("Ainda não há reservas de pré-venda.")
        return

    pre_vendas_por_id = {str(pv.get("id")): pv for pv in pre_vendas}
    for r in reservas:
        pv = pre_vendas_por_id.get(str(r.get("pre_venda_id"))) or buscar_pre_venda_por_id(r.get("pre_venda_id")) or {}
        cliente = clientes_por_id.get(str(r.get("cliente_id")), {})
        status_reserva = str(r.get("status") or "aguardando_sinal").lower()

        st.markdown(f"""
        <div class="user-card">
            <div class="user-head">
                <div>
                    <div class="user-name">{html.escape(str(pv.get('nome') or 'Pré-venda'))}</div>
                    <div class="user-email">Cliente: {html.escape(str(cliente.get('nome') or 'Cliente'))} — {html.escape(str(cliente.get('email') or '-'))}</div>
                </div>
                <div>
                    <span class="market-tag market-tag-gold">{html.escape(texto_status_reserva(status_reserva))}</span>
                </div>
            </div>
            <div class="user-info-grid">
                <div class="user-info-item"><small>Quantidade</small><strong>{int(r.get('quantidade') or 1)}</strong></div>
                <div class="user-info-item"><small>Valor total</small><strong>{money(r.get('valor_total') or 0)}</strong></div>
                <div class="user-info-item"><small>Sinal</small><strong>{money(r.get('valor_sinal') or 0)}</strong></div>
                <div class="user-info-item"><small>Restante</small><strong>{money(r.get('valor_restante') or 0)}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        a1, a2, a3, a4, a5 = st.columns(5)
        with a1:
            if st.button("🟡 Sinal pago", key=f"pv_sinal_pago_{r['id']}", disabled=status_reserva in ["incluido_na_garagem", "cancelado"]):
                atualizar_reserva_pre_venda(r["id"], {"status": "sinal_pago"})
                st.rerun()
        with a2:
            if st.button("🟢 Pago total", key=f"pv_pago_total_{r['id']}", disabled=status_reserva in ["incluido_na_garagem", "cancelado"]):
                atualizar_reserva_pre_venda(r["id"], {"status": "pago_total"})
                st.rerun()
        with a3:
            if st.button("🚗 Incluir garagem", key=f"pv_incluir_garagem_{r['id']}", disabled=status_reserva not in ["sinal_pago", "pago_total"]):
                ok, msg = efetivar_reserva_pre_venda_na_garagem(r, pv)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        with a4:
            if st.button("🔴 Cancelar", key=f"pv_cancelar_reserva_{r['id']}", disabled=status_reserva in ["incluido_na_garagem", "cancelado"]):
                atualizar_reserva_pre_venda(r["id"], {"status": "cancelado"})
                if str(pv.get("status") or "").lower() == "esgotada" and quantidade_restante_pre_venda(pv) > 0:
                    atualizar_pre_venda(pv.get("id"), {"status": "ativa"})
                st.rerun()
        with a5:
            st.caption("Libera inclusão após sinal ou total.")


def mensagem_status_reserva_cliente(status):
    status = str(status or "").lower()
    mapa = {
        "aguardando_sinal": "Aguardando pagamento do sinal. Assim que o admin confirmar, o status será atualizado aqui.",
        "sinal_pago": "✅ Sinal recebido e validado pelo admin. Sua pré-venda está garantida.",
        "pago_total": "✅ Pagamento total confirmado pelo admin. Aguarde a inclusão na garagem.",
        "incluido_na_garagem": "🚗 Mini incluída na sua garagem.",
        "cancelado": "🔴 Reserva cancelada.",
    }
    return mapa.get(status, "Status em acompanhamento pelo admin.")


def render_pre_vendas_cliente(usuario):
    st.markdown("""
    <div class="market-hero">
        <div class="market-title">🚧 Pré-venda</div>
        <p>Reserve minis em pré-venda. O admin confirma o sinal/pagamento e depois inclui na sua garagem.</p>
    </div>
    """, unsafe_allow_html=True)

    col_refresh_1, col_refresh_2 = st.columns([1, 4])
    with col_refresh_1:
        if st.button("🔄 Atualizar status", use_container_width=True, key="cliente_refresh_pre_venda_status"):
            st.rerun()
    with col_refresh_2:
        st.caption("Atualiza o status das suas reservas sem precisar apertar F5 no navegador.")

    try:
        pre_vendas = buscar_pre_vendas(apenas_ativas=True)
    except Exception as e:
        st.error(f"Não consegui carregar pré-vendas. Erro: {e}")
        return

    minhas_reservas = buscar_reservas_pre_venda(cliente_id=usuario.get("id"))

    if minhas_reservas:
        with st.expander("📌 Minhas reservas de pré-venda", expanded=True):
            pre_vendas_por_id = {str(pv.get("id")): pv for pv in pre_vendas}
            for r in minhas_reservas:
                pv = pre_vendas_por_id.get(str(r.get("pre_venda_id"))) or buscar_pre_venda_por_id(r.get("pre_venda_id")) or {}
                status_reserva = str(r.get("status") or "aguardando_sinal").lower()
                status_texto = texto_status_reserva(status_reserva)
                status_msg = mensagem_status_reserva_cliente(status_reserva)

                if status_reserva in ["sinal_pago", "pago_total", "incluido_na_garagem"]:
                    tag_class = "market-tag-ok"
                elif status_reserva == "cancelado":
                    tag_class = "market-tag-sold"
                else:
                    tag_class = "market-tag-gold"

                card_reserva_html = f"""<div class="user-card">
<div class="user-head">
<div>
<div class="user-name">{html.escape(str(pv.get('nome') or 'Pré-venda'))}</div>
<div class="user-email">Acompanhamento da sua reserva</div>
</div>
<div>
<span class="market-tag {tag_class}">{html.escape(status_texto)}</span>
</div>
</div>
<div class="user-info-grid">
<div class="user-info-item"><small>Quantidade</small><strong>{int(r.get('quantidade') or 1)}</strong></div>
<div class="user-info-item"><small>Total</small><strong>{money(r.get('valor_total') or 0)}</strong></div>
<div class="user-info-item"><small>Sinal</small><strong>{money(r.get('valor_sinal') or 0)}</strong></div>
<div class="user-info-item"><small>Restante</small><strong>{money(r.get('valor_restante') or 0)}</strong></div>
</div>
<p class="market-line" style="margin-top:14px;">
<b>Status:</b> {html.escape(status_texto)}<br>
{html.escape(status_msg)}
</p>
</div>"""
                st.markdown(card_reserva_html, unsafe_allow_html=True)
    else:
        st.info("Você ainda não possui reservas de pré-venda.")

    pre_vendas_visiveis = [pv for pv in pre_vendas if str(pv.get("status") or "").lower() in ["ativa", "esgotada"]]

    if not pre_vendas_visiveis:
        st.info("Nenhuma pré-venda disponível no momento.")
        return

    for pv in pre_vendas_visiveis:
        restante = quantidade_restante_pre_venda(pv)
        status = str(pv.get("status") or "ativa").lower()
        esgotado = restante <= 0 or status == "esgotada"
        valor_total = float(pv.get("valor_total") or 0)
        valor_sinal = float(pv.get("valor_sinal") or 0)
        valor_restante = max(0, valor_total - valor_sinal)
        foto_html = imagem_html(get_foto_item(pv), "market-img") if get_foto_item(pv) else '<div class="market-empty">🏎️</div>'

        st.markdown(f"""
        <div class="market-card">
            {foto_html}
            <div class="market-body">
                <div class="market-tags">
                    <span class="market-tag market-tag-gold">PRÉ-VENDA</span>
                    <span class="market-tag {'market-tag-sold' if esgotado else 'market-tag-ok'}">{'ESGOTADO' if esgotado else 'DISPONÍVEL'}</span>
                </div>
                <h3 class="market-name">{html.escape(str(pv.get('nome') or 'Mini'))}</h3>
                <p class="market-line"><b>Marca:</b> {html.escape(str(pv.get('marca') or '-'))}</p>
                <p class="market-line"><b>Série:</b> {html.escape(str(pv.get('serie') or '-'))}</p>
                <p class="market-line"><b>Previsão:</b> {html.escape(str(pv.get('data_prevista') or '-'))}</p>
                <p class="market-line"><b>Observação:</b> {html.escape(str(pv.get('observacao') or '-'))}</p>
                <div class="market-price-grid">
                    <div class="market-price"><small>Disponíveis</small><strong>{restante}</strong></div>
                    <div class="market-price"><small>Valor total</small><strong>{money(valor_total)}</strong></div>
                    <div class="market-price"><small>Sinal</small><strong>{money(valor_sinal)}</strong></div>
                    <div class="market-price"><small>Restante</small><strong>{money(valor_restante)}</strong></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if esgotado:
            st.warning("Pré-venda esgotada.")
            continue

        qtd = st.number_input(
            f"Quantidade para reservar — {pv.get('nome')}",
            min_value=1,
            max_value=max(1, int(restante or 1)),
            value=1,
            step=1,
            key=f"cliente_qtd_pre_venda_{pv.get('id')}"
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total da reserva", money(valor_total * int(qtd or 1)))
        with c2:
            st.metric("Sinal", money(valor_sinal * int(qtd or 1)))
        with c3:
            st.metric("Restante", money(valor_restante * int(qtd or 1)))

        if st.button("🚧 Reservar pré-venda", key=f"cliente_reservar_pv_{pv.get('id')}", use_container_width=True):
            try:
                pv_atualizada = buscar_pre_venda_por_id(pv.get("id")) or pv
                ok, msg = criar_reserva_pre_venda(pv_atualizada, usuario.get("id"), int(qtd or 1))
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            except Exception as e:
                st.error(f"Erro ao criar reserva: {e}")


# =========================
# ESTOQUE LOJA — compatível sem coluna nova no Supabase
# =========================
def obter_estoque_loja_item(item):
    """
    Lê a quantidade oficial de estoque do item da loja.

    Prioridade:
    1) colunas reais, se existirem no Supabase: estoque, quantidade, qtd, disponiveis
    2) campo destaque no formato: Qtd: 2
    3) fallback antigo: se status vendido = 0, senão = 1
    """
    if not item:
        return 0

    for campo in ["estoque", "quantidade", "qtd", "disponiveis"]:
        try:
            valor = item.get(campo)
            if valor is not None and str(valor).strip() != "":
                return max(0, int(float(valor)))
        except Exception:
            pass

    destaque = str(item.get("destaque") or "")
    m = re.search(r"(?:qtd|qtde|quantidade|estoque|dispon[ií]veis)\s*[:=]\s*(\d+)", destaque, flags=re.IGNORECASE)
    if m:
        try:
            return max(0, int(m.group(1)))
        except Exception:
            pass

    status = str(item.get("status") or "").strip().lower()
    if status == "vendido":
        return 0

    return 1


def texto_unidades_estoque(qtd):
    try:
        qtd = int(qtd or 0)
    except Exception:
        qtd = 0
    if qtd <= 0:
        return "Esgotado"
    if qtd == 1:
        return "1 unidade"
    return f"{qtd} unidades"


def badge_estoque_loja(qtd):
    try:
        qtd = int(qtd or 0)
    except Exception:
        qtd = 0

    if qtd <= 0:
        return '<span class="market-tag market-tag-sold">ESGOTADO</span>'
    return '<span class="market-tag market-tag-ok">DISPONÍVEL</span>'


def atualizar_destaque_com_qtd(destaque, qtd):
    """
    Guarda a quantidade no próprio campo destaque:
    Ex: 'Promoção' + qtd 2 => 'Qtd: 2 | Promoção'
    Ex: 'Qtd: 1 | Promoção' + qtd 3 => 'Qtd: 3 | Promoção'
    """
    try:
        qtd = max(0, int(qtd or 0))
    except Exception:
        qtd = 0

    texto = str(destaque or "").strip()
    texto = re.sub(r"^\s*(?:qtd|qtde|quantidade|estoque|dispon[ií]veis)\s*[:=]\s*\d+\s*(?:\|\s*)?", "", texto, flags=re.IGNORECASE).strip()
    if texto:
        return f"Qtd: {qtd} | {texto}"
    return f"Qtd: {qtd}"


CATEGORIAS_LOJA = ["Mainline", "Silver Séries", "Premium", "Mini GT", "CCA", "Outros"]


def normalizar_categoria_loja(valor):
    texto = str(valor or "").strip()
    mapa = {
        "mainline": "Mainline",
        "main line": "Mainline",
        "silver series": "Silver Séries",
        "silver séries": "Silver Séries",
        "silver serie": "Silver Séries",
        "silver série": "Silver Séries",
        "premium": "Premium",
        "mini gt": "Mini GT",
        "minigt": "Mini GT",
        "cca": "CCA",
        "outros": "Outros",
        "outro": "Outros",
    }
    chave = texto.lower()
    return mapa.get(chave, texto if texto in CATEGORIAS_LOJA else "Outros")


def obter_categoria_loja_item(item):
    """Lê a categoria da loja sem exigir coluna nova no Supabase."""
    if not item:
        return "Outros"

    for campo in ["categoria", "category", "grupo", "linha_loja"]:
        valor = item.get(campo)
        if valor:
            return normalizar_categoria_loja(valor)

    destaque = str(item.get("destaque") or "")
    m = re.search(r"(?:categoria|category|grupo|linha)\s*[:=]\s*([^|]+)", destaque, flags=re.IGNORECASE)
    if m:
        return normalizar_categoria_loja(m.group(1).strip())

    serie = str(item.get("serie") or "")
    categoria_serie = normalizar_categoria_loja(serie)
    if categoria_serie != "Outros":
        return categoria_serie

    texto = " ".join([
        str(item.get("nome") or ""),
        str(item.get("marca") or ""),
        str(item.get("serie") or ""),
        str(item.get("raridade") or ""),
    ]).lower()

    if "mini gt" in texto or "minigt" in texto:
        return "Mini GT"
    if "cca" in texto:
        return "CCA"
    if "silver" in texto:
        return "Silver Séries"
    if "premium" in texto:
        return "Premium"
    if "mainline" in texto or "main line" in texto:
        return "Mainline"

    return "Outros"


def limpar_metadados_destaque_loja(destaque):
    texto = str(destaque or "").strip()
    partes = [p.strip() for p in texto.split("|") if p.strip()]
    partes_limpas = []
    for parte in partes:
        if re.match(r"^(?:qtd|qtde|quantidade|estoque|dispon[ií]veis)\s*[:=]", parte, flags=re.IGNORECASE):
            continue
        if re.match(r"^(?:categoria|category|grupo|linha)\s*[:=]", parte, flags=re.IGNORECASE):
            continue
        partes_limpas.append(parte)
    return " | ".join(partes_limpas).strip()


def atualizar_destaque_com_qtd_e_categoria(destaque, qtd, categoria):
    try:
        qtd = max(0, int(qtd or 0))
    except Exception:
        qtd = 0
    categoria = normalizar_categoria_loja(categoria)
    texto = limpar_metadados_destaque_loja(destaque)
    prefixo = f"Qtd: {qtd} | Categoria: {categoria}"
    return f"{prefixo} | {texto}" if texto else prefixo


def dados_estoque_loja_para_update(destaque, qtd, status=None):
    """
    Monta update sem depender de coluna estoque.
    Assim não quebra caso a tabela loja_minis só tenha o campo destaque.
    """
    try:
        qtd = max(0, int(qtd or 0))
    except Exception:
        qtd = 0

    categoria_atual = "Outros"
    m_cat = re.search(r"(?:categoria|category|grupo|linha)\s*[:=]\s*([^|]+)", str(destaque or ""), flags=re.IGNORECASE)
    if m_cat:
        categoria_atual = normalizar_categoria_loja(m_cat.group(1).strip())

    dados = {"destaque": atualizar_destaque_com_qtd_e_categoria(destaque, qtd, categoria_atual)}

    if status is not None:
        dados["status"] = status
    else:
        dados["status"] = "vendido" if qtd <= 0 else "disponivel"

    return dados


def baixar_estoque_loja_item(item, quantidade=1):
    """Baixa estoque do item da loja e marca vendido apenas quando chegar em zero."""
    if not item:
        return 0

    try:
        quantidade = max(1, int(quantidade or 1))
    except Exception:
        quantidade = 1

    atual = obter_estoque_loja_item(item)
    novo = max(0, atual - quantidade)

    dados = dados_estoque_loja_para_update(item.get("destaque") or "", novo)
    atualizar_loja_mini(item.get("id"), dados)
    return novo


def buscar_loja_item_por_id(loja_id):
    if not loja_id:
        return None
    try:
        resp = (
            supabase.table("loja_minis")
            .select("*")
            .eq("id", loja_id)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception:
        return None


def criar_pedido_loja(usuario_id, loja_item, observacoes=""):
    """Cria um pedido/reserva a partir de uma mini publicada na loja."""
    dados = {
        "usuario_id": usuario_id,
        "loja_mini_id": loja_item.get("id"),
        "nome": loja_item.get("nome") or "",
        "marca": loja_item.get("marca") or "",
        "serie": loja_item.get("serie") or "",
        "ano": loja_item.get("ano") or "",
        "raridade": loja_item.get("raridade") or "Comum",
        "valor": float(loja_item.get("valor") or 0),
        "valor_estimado": float(loja_item.get("valor_estimado") or 0),
        "foto_url": loja_item.get("foto_url") or "",
        "status": "solicitado",
        "observacoes": observacoes or "Solicitado pela loja"
    }
    supabase.table("pedidos").insert(dados).execute()


def buscar_pedidos(usuario_id=None):
    query = supabase.table("pedidos").select("*")
    if usuario_id is not None:
        query = query.eq("usuario_id", usuario_id)
    return query.order("criado_em", desc=True).execute().data


def pedido_aberto_existe(usuario_id, loja_mini_id):
    """Evita pedido duplicado para a mesma mini enquanto ainda estiver em aberto."""
    try:
        pedidos = (
            supabase.table("pedidos")
            .select("id,status")
            .eq("usuario_id", usuario_id)
            .eq("loja_mini_id", loja_mini_id)
            .in_("status", ["solicitado", "pendente", "reservado", "aguardando_pix", "pago"])
            .execute()
            .data
        )
        return bool(pedidos)
    except Exception:
        return False


def atualizar_pedido(pedido_id, dados):
    supabase.table("pedidos").update(dados).eq("id", pedido_id).execute()


def excluir_pedido(pedido_id):
    supabase.table("pedidos").delete().eq("id", pedido_id).execute()



def concluir_pedido_na_garagem(pedido, loja_item=None):
    """Marca o pedido como pago/concluído, lança a mini na garagem e marca a loja como vendido."""
    loja_item = loja_item or {}

    if not pedido.get("usuario_id"):
        return False, "Pedido sem cliente vinculado."

    if (pedido.get("status") or "").lower() == "concluido":
        return False, "Este pedido já está concluído."

    cadastrar_mini(
        pedido.get("usuario_id"),
        pedido.get("nome") or loja_item.get("nome") or "Mini da loja",
        pedido.get("marca") or loja_item.get("marca") or "Hot Wheels",
        pedido.get("serie") or loja_item.get("serie") or "",
        pedido.get("ano") or loja_item.get("ano") or "",
        pedido.get("raridade") or loja_item.get("raridade") or "Comum",
        float(pedido.get("valor") or loja_item.get("valor") or 0),
        float(pedido.get("valor_estimado") or loja_item.get("valor_estimado") or 0),
        pedido.get("foto_url") or loja_item.get("foto_url") or "",
        "pago",
        "loja",
        "Origem: Loja / Pedido concluído"
    )

    atualizar_pedido(pedido["id"], {"status": "concluido"})

    if pedido.get("loja_mini_id"):
        try:
            item_atualizado = buscar_loja_item_por_id(pedido.get("loja_mini_id")) or loja_item
            baixar_estoque_loja_item(item_atualizado, 1)
        except Exception:
            pass

    return True, "Pedido pago, mini lançada na garagem e estoque da loja atualizado."


def atualizar_nivel_cliente(usuario_id, nivel_cliente):
    supabase.table("usuarios").update({"nivel_cliente": nivel_cliente}).eq("id", usuario_id).execute()


def listar_usuarios():
    return supabase.table("usuarios").select("*").order("criado_em", desc=True).execute().data


def parse_data_supabase(valor):
    """Converte datas do Supabase com segurança para datetime."""
    if not valor:
        return None

    texto = str(valor).strip()

    try:
        if texto.endswith("Z"):
            texto = texto[:-1] + "+00:00"
        return datetime.fromisoformat(texto)
    except Exception:
        pass

    for formato in [
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            return datetime.strptime(texto[:26], formato)
        except Exception:
            pass

    return None


def contar_cadastros_novos(usuarios, dias):
    """Conta usuários criados nos últimos N dias, ignorando admins."""
    agora = datetime.now()
    total = 0

    for usuario in usuarios or []:
        if str(usuario.get("tipo") or "usuario").lower() == "admin":
            continue

        criado = parse_data_supabase(usuario.get("criado_em"))
        if not criado:
            continue

        # Remove timezone para comparar com datetime.now() local sem quebrar.
        if getattr(criado, "tzinfo", None) is not None:
            criado = criado.replace(tzinfo=None)

        delta = agora - criado
        if delta.days < dias and delta.total_seconds() >= 0:
            total += 1

    return total


def atualizar_status(usuario_id, status):
    supabase.table("usuarios").update({"status": status}).eq("id", usuario_id).execute()


def excluir_cliente_completo(usuario_id):
    """Exclui definitivamente um cliente e seus dados vinculados.

    Ordem segura: primeiro remove registros filhos, depois remove o usuário.
    Usa try/except nos vínculos opcionais para não travar se alguma tabela não existir.
    """
    if not usuario_id:
        return False, "Cliente inválido."

    try:
        supabase.table("minis").delete().eq("usuario_id", usuario_id).execute()
    except Exception:
        pass

    try:
        supabase.table("pedidos").delete().eq("usuario_id", usuario_id).execute()
    except Exception:
        pass

    try:
        supabase.table("scanner_logs").delete().eq("usuario_id", usuario_id).execute()
    except Exception:
        pass

    try:
        supabase.table("usuarios").delete().eq("id", usuario_id).execute()
        return True, "Cliente excluído definitivamente da GarageHub."
    except Exception as e:
        return False, f"Erro ao excluir cliente: {e}"


def criar_usuario(nome, email, senha, telefone, cidade, estado, instagram, foto_perfil_url, codigo_convite=""):
    if not nome or not email or not senha:
        return False, "Preencha nome, e-mail e senha."

    codigo_membro = f"GHW-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    dados = {
        "nome": nome.strip(),
        "email": email.strip().lower(),
        "senha": senha,
        "tipo": "usuario",
        "status": "ativo",
        "codigo_membro": codigo_membro,
        "telefone": telefone,
        "cidade": cidade,
        "estado": estado,
        "instagram": instagram,
        "foto_perfil_url": foto_perfil_url or "",
        "nivel_cliente": "comum"
    }

    try:
        supabase.table("usuarios").insert(dados).execute()
        return True, "Conta criada com sucesso. Você entrou como cliente comum."
    except Exception:
        dados.pop("nivel_cliente", None)
        try:
            supabase.table("usuarios").insert(dados).execute()
            return True, "Conta criada com sucesso."
        except Exception as e:
            return False, f"Erro ao criar usuário: {e}"


def criar_cliente_admin(nome, email, senha, telefone, cidade, estado, instagram, foto_perfil_url):
    if not nome or not email:
        return False, "Preencha nome e e-mail do cliente."

    codigo_membro = f"GHW-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    try:
        supabase.table("usuarios").insert({
            "nome": nome.strip(),
            "email": email.strip().lower(),
            "senha": "primeiro_acesso",
            "tipo": "usuario",
            "status": "ativo",
            "codigo_membro": codigo_membro,
            "telefone": telefone,
            "cidade": cidade,
            "estado": estado,
            "instagram": instagram,
            "foto_perfil_url": foto_perfil_url or "",
            "nivel_cliente": "comum"
        }).execute()
        return True, "Cliente criado com sucesso. No primeiro acesso ele deverá criar a própria senha."
    except Exception as e:
        return False, f"Erro ao criar cliente: {e}"





# =========================
# ADMIN — GARAGEM DO CLIENTE
# =========================
def render_admin_garagem_cliente(usuario_cliente):
    st.markdown(f"""
    <div class="admin-work-card">
        <h3>🚗 Garagem de {html.escape(str(usuario_cliente.get("nome") or "Cliente"))}</h3>
        <p>Edite minis, valores, raridade, status e informações da coleção deste cliente.</p>
    </div>
    """, unsafe_allow_html=True)

    col_admin_voltar, col_admin_refresh = st.columns([1, 1])
    with col_admin_voltar:
        if st.button("⬅️ Voltar para usuários", use_container_width=True, key="voltar_admin_usuarios"):
            st.session_state.pop("admin_cliente_garagem_id", None)
            st.rerun()

    with col_admin_refresh:
        if st.button("🔄 Atualizar dados do cliente", use_container_width=True, key=f"admin_refresh_garagem_cliente_{usuario_cliente.get('id')}"):
            try:
                st.cache_data.clear()
            except Exception:
                pass
            try:
                st.cache_resource.clear()
            except Exception:
                pass
            st.rerun()

    st.caption("Use este botão depois de lançar pré-vendas antigas ou minis manualmente para recarregar a garagem direto do Supabase.")

    # =========================
    # ADMIN — LANÇAR MINI DA LOJA NA GARAGEM DO CLIENTE
    # =========================
    st.markdown("""
    <div class="admin-work-card">
        <h3>🛒 Inserir mini da Loja nesta garagem</h3>
        <p>Selecione um item cadastrado na Loja, lance na garagem do cliente e baixe 1 unidade do estoque automaticamente.</p>
    </div>
    """, unsafe_allow_html=True)

    try:
        loja_minis_para_lancar = buscar_loja_minis(apenas_disponiveis=False) or []
    except Exception as e:
        loja_minis_para_lancar = []
        st.warning(f"Não consegui carregar a Loja para lançamento manual: {e}")

    loja_minis_para_lancar = [
        item for item in loja_minis_para_lancar
        if obter_estoque_loja_item(item) > 0
        and str(item.get("status") or "disponivel").strip().lower() != "vendido"
    ]

    if not loja_minis_para_lancar:
        st.info("Nenhum item com estoque disponível na Loja para lançar nesta garagem.")
    else:
        opcoes_loja_cliente = {}
        for item in loja_minis_para_lancar:
            estoque_item = obter_estoque_loja_item(item)
            rotulo = (
                f"#{item.get('id')} - {item.get('nome', 'Mini')} "
                f"| {money(item.get('valor') or 0)} "
                f"| estoque: {estoque_item}"
            )
            opcoes_loja_cliente[rotulo] = item

        escolha_loja_cliente = st.selectbox(
            "Escolha a mini da Loja para inserir neste cliente",
            list(opcoes_loja_cliente.keys()),
            key=f"admin_loja_para_cliente_{usuario_cliente.get('id')}"
        )

        item_loja_escolhido = opcoes_loja_cliente.get(escolha_loja_cliente)
        if item_loja_escolhido:
            estoque_atual_loja = obter_estoque_loja_item(item_loja_escolhido)

            quantidade_lancamento = st.number_input(
                "Quantidade para inserir nesta garagem",
                min_value=1,
                max_value=max(1, int(estoque_atual_loja or 1)),
                value=1,
                step=1,
                key=f"admin_qtd_lancar_loja_cliente_{usuario_cliente.get('id')}"
            )

            quantidade_lancamento = int(quantidade_lancamento or 1)

            c_loja_1, c_loja_2, c_loja_3 = st.columns([1, 1, 1])
            with c_loja_1:
                st.metric("Estoque atual", estoque_atual_loja)
            with c_loja_2:
                st.metric("Valor venda", money(item_loja_escolhido.get("valor") or 0))
            with c_loja_3:
                st.metric("Após lançar", max(0, estoque_atual_loja - quantidade_lancamento))

            status_lancamento = st.selectbox(
                "Status de pagamento para lançar na garagem",
                ["pago", "pendente", "reservado", "pre_datado"],
                index=0,
                key=f"admin_status_lancar_loja_cliente_{usuario_cliente.get('id')}"
            )

            data_pagamento_lancamento = None
            if status_lancamento in ["pendente", "reservado", "pre_datado"]:
                data_pagamento_lancamento = st.date_input(
                    "Data prevista de pagamento (opcional)",
                    value=None,
                    format="DD/MM/YYYY",
                    key=f"admin_data_pagamento_lancar_loja_cliente_{usuario_cliente.get('id')}"
                )

            observacao_lancamento = st.text_input(
                "Observação opcional",
                value="Lançado manualmente pelo admin a partir da Loja",
                key=f"admin_obs_lancar_loja_cliente_{usuario_cliente.get('id')}"
            )

            if st.button(
                "➕ Inserir quantidade na garagem e baixar estoque",
                use_container_width=True,
                key=f"admin_lancar_loja_cliente_{usuario_cliente.get('id')}"
            ):
                try:
                    item_atualizado = buscar_loja_item_por_id(item_loja_escolhido.get("id")) or item_loja_escolhido
                    estoque_real = obter_estoque_loja_item(item_atualizado)
                    quantidade_lancamento = int(quantidade_lancamento or 1)

                    if estoque_real <= 0:
                        st.error("Este item não possui estoque disponível na Loja.")
                    elif quantidade_lancamento > estoque_real:
                        st.error(f"Quantidade solicitada ({quantidade_lancamento}) maior que o estoque disponível ({estoque_real}).")
                    else:
                        for _ in range(quantidade_lancamento):
                            cadastrar_mini(
                                usuario_cliente.get("id"),
                                item_atualizado.get("nome") or "Mini da loja",
                                item_atualizado.get("marca") or "Hot Wheels",
                                item_atualizado.get("serie") or "",
                                item_atualizado.get("ano") or "",
                                item_atualizado.get("raridade") or "Comum",
                                float(item_atualizado.get("valor") or 0),
                                float(item_atualizado.get("valor_estimado") or item_atualizado.get("valor") or 0),
                                item_atualizado.get("foto_url") or "",
                                status_lancamento,
                                "loja",
                                observacao_lancamento or "Lançado pelo admin a partir da Loja",
                                data_pagamento_lancamento
                            )

                        novo_estoque = baixar_estoque_loja_item(item_atualizado, quantidade_lancamento)
                        st.success(f"{quantidade_lancamento} mini(s) lançada(s) na garagem. Estoque atualizado para {novo_estoque} unidade(s).")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro ao lançar mini da Loja na garagem: {e}")

    # =========================
    # ADMIN — INSERIR MINI MANUAL / MIGRAÇÃO DIRETO NA GARAGEM
    # =========================
    st.markdown("""
    <div class="admin-work-card">
        <h3>✍️ Inserir mini manual / migração</h3>
        <p>Use este caminho para acervo migrado de plataforma antiga. Não cadastra na Loja, não baixa estoque e poderá ser excluído pela própria garagem do cliente.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("➕ Adicionar mini direto na garagem do cliente", expanded=False):
        with st.form(f"form_admin_mini_manual_cliente_{usuario_cliente.get('id')}"):
            mc1, mc2 = st.columns(2)

            with mc1:
                manual_nome = st.text_input("Nome da mini *", key=f"manual_nome_{usuario_cliente.get('id')}")
                manual_marca = st.text_input("Marca", value="Hot Wheels", key=f"manual_marca_{usuario_cliente.get('id')}")
                manual_serie = st.text_input("Série / linha", key=f"manual_serie_{usuario_cliente.get('id')}")
                manual_ano = st.text_input("Ano", key=f"manual_ano_{usuario_cliente.get('id')}")
                manual_foto = st.file_uploader("Foto da mini", type=["png", "jpg", "jpeg"], key=f"manual_foto_{usuario_cliente.get('id')}")

            with mc2:
                manual_raridade = st.selectbox(
                    "Raridade",
                    ["Comum", "TH", "STH", "Premium", "RLC", "Chase", "Especial", "Limitado", "Não identificado"],
                    key=f"manual_raridade_{usuario_cliente.get('id')}"
                )
                manual_valor_pago = st.number_input("Valor pago", min_value=0.0, step=1.0, value=0.0, key=f"manual_valor_pago_{usuario_cliente.get('id')}")
                manual_valor_estimado = st.number_input("Valor estimado", min_value=0.0, step=1.0, value=0.0, key=f"manual_valor_estimado_{usuario_cliente.get('id')}")
                manual_status = st.selectbox("Status pagamento", ["pago", "pendente", "reservado", "cancelado"], index=0, key=f"manual_status_{usuario_cliente.get('id')}")
                manual_data_pagamento = st.date_input(
                    "Data prevista de pagamento (opcional)",
                    value=None,
                    format="DD/MM/YYYY",
                    key=f"manual_data_pagamento_{usuario_cliente.get('id')}"
                )

            manual_obs = st.text_area(
                "Observação / origem",
                value="Origem: manual / migração de plataforma antiga",
                key=f"manual_obs_{usuario_cliente.get('id')}"
            )

            salvar_manual = st.form_submit_button("💾 Salvar mini manual na garagem")

            if salvar_manual:
                if not str(manual_nome or "").strip():
                    st.error("Informe o nome da mini para salvar na garagem do cliente.")
                else:
                    try:
                        manual_foto_url = upload_storage(
                            manual_foto,
                            "minis-migracao",
                            f"cliente_{usuario_cliente.get('id')}_{manual_nome}"
                        ) if manual_foto is not None else ""

                        cadastrar_mini(
                            usuario_cliente.get("id"),
                            manual_nome,
                            manual_marca,
                            manual_serie,
                            manual_ano,
                            manual_raridade,
                            float(manual_valor_pago or 0),
                            float(manual_valor_estimado or manual_valor_pago or 0),
                            manual_foto_url,
                            manual_status,
                            "manual_migracao",
                            manual_obs or "Origem: manual / migração",
                            manual_data_pagamento
                        )
                        st.success("Mini manual/migração incluída na garagem do cliente. Não alterou estoque da Loja.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao incluir mini manual na garagem: {e}")

    minis_cliente = buscar_minis(usuario_cliente.get("id"))

    if not minis_cliente:
        st.info("Este cliente ainda não possui minis cadastrados. Use o bloco da Loja ou o bloco Manual/Migração acima para inserir minis nesta garagem.")
        return

    busca_admin = st.text_input(
        "Buscar mini deste cliente",
        placeholder="Digite nome, marca ou série...",
        key=f"admin_busca_mini_cliente_{usuario_cliente.get('id')}"
    ).strip().lower()

    if busca_admin:
        minis_cliente = [
            m for m in minis_cliente
            if busca_admin in str(m.get("nome") or "").lower()
            or busca_admin in str(m.get("marca") or "").lower()
            or busca_admin in str(m.get("serie") or "").lower()
        ]

    st.caption(f"Exibindo {len(minis_cliente)} mini(s) deste cliente.")

    for mini in minis_cliente:
        mini_id = mini.get("id")
        nome_atual = limpar_campo_visual(mini.get("nome"), "Mini sem nome")
        marca_atual = limpar_campo_visual(mini.get("marca"), "")
        serie_atual = limpar_campo_visual(mini.get("serie"), "")
        ano_atual = limpar_campo_visual(mini.get("ano"), "")
        raridade_atual = limpar_campo_visual(mini.get("raridade"), "Comum")
        status_atual = limpar_campo_visual(mini.get("status_pagamento"), "pendente")
        tipo_atual = limpar_campo_visual(mini.get("tipo_mini"), "compra")
        destaque_atual = limpar_campo_visual(mini.get("destaque_cliente"), "")
        foto_atual = get_foto_item(mini)
        origem_atual = origem_operacional_mini(mini)
        origem_label = "Manual/Migração" if origem_atual == "manual" else "Loja/Protegida"

        with st.expander(f"🚗 {nome_atual} — {money(mini.get('valor_estimado') or 0)} — {origem_label}", expanded=False):
            col_foto, col_form = st.columns([0.9, 2.1])

            with col_foto:
                src_foto = foto_src(foto_atual)
                if src_foto:
                    st.markdown(
                        f"""
                        <div class="garage-photo-box">
                            <img src="{html.escape(src_foto, quote=True)}" loading="lazy" referrerpolicy="no-referrer">
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown("<div class='garage-photo-box garage-empty'>🏎️</div>", unsafe_allow_html=True)

                nova_foto = st.file_uploader("Trocar foto", type=["png", "jpg", "jpeg"], key=f"admin_foto_mini_{mini_id}")

            with col_form:
                c1, c2 = st.columns(2)

                with c1:
                    novo_nome = st.text_input("Nome", value=nome_atual, key=f"admin_nome_mini_{mini_id}")
                    nova_marca = st.text_input("Marca", value=marca_atual, key=f"admin_marca_mini_{mini_id}")
                    nova_serie = st.text_input("Série", value=serie_atual, key=f"admin_serie_mini_{mini_id}")
                    novo_ano = st.text_input("Ano", value=ano_atual, key=f"admin_ano_mini_{mini_id}")

                with c2:
                    opcoes_raridade = ["Comum", "TH", "STH", "Premium", "RLC", "Chase", "Especial", "Limitado", "Não identificado"]
                    idx_raridade = opcoes_raridade.index(raridade_atual) if raridade_atual in opcoes_raridade else 0
                    nova_raridade = st.selectbox("Raridade", opcoes_raridade, index=idx_raridade, key=f"admin_raridade_mini_{mini_id}")

                    novo_valor_pago = st.number_input("Valor pago", min_value=0.0, step=1.0, value=float(mini.get("valor_pago") or 0), key=f"admin_valor_pago_mini_{mini_id}")
                    novo_valor_estimado = st.number_input("Valor estimado", min_value=0.0, step=1.0, value=float(mini.get("valor_estimado") or 0), key=f"admin_valor_estimado_mini_{mini_id}")

                    opcoes_status = ["pendente", "pago", "reservado", "cancelado"]
                    idx_status = opcoes_status.index(status_atual.lower()) if status_atual.lower() in opcoes_status else 0
                    novo_status = st.selectbox("Status pagamento", opcoes_status, index=idx_status, key=f"admin_status_mini_{mini_id}")
                    data_atual_pagamento = normalizar_data_pagamento_prevista(mini.get("data_pagamento_prevista"))
                    nova_data_pagamento = st.date_input(
                        "Data prevista de pagamento (opcional)",
                        value=data_atual_pagamento,
                        format="DD/MM/YYYY",
                        key=f"admin_data_pagamento_mini_{mini_id}"
                    )

                opcoes_tipo = ["loja", "manual_migracao", "compra", "scanner", "presente", "troca", "colecao", "pre_venda"]
                idx_tipo = opcoes_tipo.index(tipo_atual.lower()) if tipo_atual.lower() in opcoes_tipo else 0
                novo_tipo = st.selectbox("Tipo da mini", opcoes_tipo, index=idx_tipo, key=f"admin_tipo_mini_{mini_id}")

                novo_destaque = st.text_area("Destaque / observação", value=destaque_atual, key=f"admin_destaque_mini_{mini_id}")

                b1, b2 = st.columns(2)

                with b1:
                    if st.button("💾 Salvar alterações", use_container_width=True, key=f"admin_salvar_mini_{mini_id}"):
                        dados_update = {
                            "nome": novo_nome,
                            "marca": nova_marca,
                            "serie": nova_serie,
                            "ano": novo_ano,
                            "raridade": nova_raridade,
                            "valor_pago": float(novo_valor_pago or 0),
                            "valor_estimado": float(novo_valor_estimado or 0),
                            "status_pagamento": novo_status,
                            "tipo_mini": novo_tipo,
                            "destaque_cliente": novo_destaque,
                            "data_pagamento_prevista": str(nova_data_pagamento) if nova_data_pagamento else None
                        }

                        if nova_foto is not None:
                            foto_url = upload_storage(nova_foto, "minis", f"admin_cliente_{usuario_cliente.get('id')}_mini_{mini_id}")
                            dados_update["foto_url"] = foto_url

                        try:
                            atualizar_mini(mini_id, dados_update)
                            st.success("Mini atualizada com sucesso.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao atualizar mini: {e}")

                with b2:
                    if pode_excluir_mini_pela_garagem(mini):
                        st.info("Origem manual/migração: esta mini pode ser excluída por aqui.")
                        confirmar_excluir = st.checkbox("Confirmar exclusão", key=f"admin_confirmar_excluir_mini_{mini_id}")
                        if st.button("🗑️ Excluir mini manual", use_container_width=True, key=f"admin_excluir_mini_{mini_id}"):
                            if not confirmar_excluir:
                                st.warning("Marque confirmar exclusão antes de apagar.")
                            else:
                                try:
                                    excluir_mini(mini_id)
                                    st.success("Mini manual/migração excluída da garagem do cliente.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao excluir mini: {e}")
                    else:
                        st.warning("Mini com origem Loja/compra/pré-venda: exclusão bloqueada nesta garagem. Remova/controle pela Loja/Admin da Loja para proteger estoque e histórico.")


# =========================
# PERFIL PREMIUM GARAGEHUB
# =========================
def render_perfil_premium(usuario, minis_usuario):
    total_minis = len(minis_usuario or [])
    valor_total = sum(float(m.get("valor_estimado") or 0) for m in (minis_usuario or []))

    bio = usuario.get("bio") or "Colecionador GarageHub"
    instagram = usuario.get("instagram_url") or usuario.get("instagram") or "@garagehub"
    mini_favorita = usuario.get("mini_favorita") or "Não definida"
    capa = usuario.get("capa_url") or ""

    capa_html = ""
    if capa:
        capa_html = f'''
        <img src="{capa}" style="
            width:100%;
            height:260px;
            object-fit:cover;
            border-radius:26px;
            margin-bottom:18px;
            border:2px solid rgba(250,204,21,.35);
        ">
        '''

    st.markdown(f'''
    <div class="profile-banner">
        {capa_html}

        <div style="display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap;align-items:center;">

            <div style="flex:1;min-width:280px;">
                <h2>🏁 {usuario.get("nome","Colecionador")}</h2>

                <p style="color:#cbd5e1;font-weight:800;font-size:16px;">
                    {bio}
                </p>

                <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap;">
                    <span class="sidebar-chip">📸 {instagram}</span>
                    <span class="sidebar-chip">🏆 {mini_favorita}</span>
                    <span class="sidebar-chip">🚗 {total_minis} minis</span>
                </div>
            </div>

            <div style="
                background:rgba(15,23,42,.78);
                border:1px solid rgba(250,204,21,.22);
                border-radius:22px;
                padding:18px;
                min-width:240px;
            ">
                <div style="color:#94a3b8;font-weight:900;font-size:12px;">
                    VALOR ESTIMADO DA GARAGEM
                </div>

                <div style="
                    color:#facc15;
                    font-size:34px;
                    font-weight:950;
                    margin-top:8px;
                ">
                    {money(valor_total)}
                </div>
            </div>

        </div>
    </div>
    ''', unsafe_allow_html=True)




# =========================
# DASHBOARD EXECUTIVO PREMIUM
# =========================
def render_dashboard_executivo(usuario, minis):
    minis = minis or []

    total = len(minis)
    valor_total = sum(float(m.get("valor_estimado") or 0) for m in minis)

    favoritas = [m for m in minis if m.get("favorito")]
    total_favoritas = len(favoritas)

    raras = [
        m for m in minis
        if str(m.get("raridade") or "").lower() in ["sth", "rlc", "chase", "premium", "especial"]
    ]

    mini_cara = None
    if minis:
        mini_cara = max(
            minis,
            key=lambda x: float(x.get("valor_estimado") or 0)
        )

    st.markdown("""
    <div class="pro-hero">
        <h2>📊 Dashboard Executivo</h2>
        <p>Visão estratégica da sua garagem premium.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">🚗</div>
            <h2>{total}</h2>
            <p>Total Minis</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">💰</div>
            <h2>{money(valor_total)}</h2>
            <p>Valor Coleção</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">🏆</div>
            <h2>{len(raras)}</h2>
            <p>Minis Raras</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">❤️</div>
            <h2>{total_favoritas}</h2>
            <p>Favoritas</p>
        </div>
        """, unsafe_allow_html=True)

    if mini_cara:
        foto = get_foto_item(mini_cara)
        foto_html = imagem_html(foto, "market-img")

        st.markdown(f"""
        <div class="market-card hall-glow">
            {foto_html}

            <div class="market-body">
                <div>
                    <div class="market-tag market-tag-vip">👑 MINI MAIS VALIOSA</div>

                    <h2 class="market-name">
                        {mini_cara.get("nome","Mini")}
                    </h2>

                    <p class="market-line">
                        Marca: <b>{mini_cara.get("marca","-")}</b>
                    </p>

                    <p class="market-line">
                        Série: <b>{mini_cara.get("serie","-")}</b>
                    </p>

                    <p class="market-line">
                        Raridade: <b>{mini_cara.get("raridade","-")}</b>
                    </p>
                </div>

                <div class="market-price-grid">
                    <div class="market-price">
                        <small>VALOR ESTIMADO</small>
                        <strong>{money(mini_cara.get("valor_estimado") or 0)}</strong>
                    </div>

                    <div class="market-price">
                        <small>VALOR PAGO</small>
                        <strong>{money(mini_cara.get("valor_pago") or 0)}</strong>
                    </div>

                    <div class="market-price">
                        <small>NÍVEL</small>
                        <strong>ELITE</strong>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)




# =========================
# SCANNER MOBILE GARAGEHUB V1
# =========================

# =========================
# SCANNER MANUAL PREMIUM
# =========================
def render_scanner_mobile(usuario):
    st.markdown("""
    <div class="pro-hero">
        <h2>📷 Scanner Manual Premium</h2>
        <p>Envie a foto do mini, confira o preview e cadastre com segurança na garagem.</p>
    </div>
    """, unsafe_allow_html=True)

    foto = st.file_uploader(
        "📸 Tirar/enviar foto da mini",
        type=["png", "jpg", "jpeg"],
        key="scanner_manual_upload"
    )

    if foto:
        st.image(foto, use_container_width=True)

        st.markdown("""
        <div class="lab-card">
            <h3>✅ Cadastro seguro</h3>
            <p>
            Sem IA inventando dados. Você preenche o correto e a GarageHub salva com a foto na sua coleção.
            </p>
        </div>
        """, unsafe_allow_html=True)

        nome = st.text_input("Nome da mini", key="scanner_manual_nome")

        marca = st.selectbox(
            "Marca",
            [
                "Hot Wheels",
                "MiniGT",
                "Kaido House",
                "Matchbox",
                "Tomica",
                "M2 Machines",
                "GreenLight",
                "Tarmac Works",
                "Inno64",
                "Johnny Lightning",
                "Outro"
            ],
            key="scanner_manual_marca"
        )

        serie = st.text_input("Série / Linha", key="scanner_manual_serie")

        ano = st.text_input("Ano", key="scanner_manual_ano")

        raridade = st.selectbox(
            "Raridade",
            [
                "Comum",
                "TH",
                "STH",
                "Premium",
                "RLC",
                "Chase",
                "Especial",
                "Limitado",
                "Não identificado"
            ],
            key="scanner_manual_raridade"
        )

        valor_pago = st.number_input(
            "Valor pago",
            min_value=0.0,
            step=1.0,
            key="scanner_manual_valor_pago"
        )

        valor_estimado = st.number_input(
            "Valor estimado",
            min_value=0.0,
            step=1.0,
            key="scanner_manual_valor_estimado"
        )

        destaque = st.text_area(
            "Observações / destaque",
            placeholder="Ex: comprado em feira, blister perfeito, edição especial...",
            key="scanner_manual_destaque"
        )

        if st.button("🚀 Salvar mini na garagem", use_container_width=True):
            if not nome:
                st.error("Informe pelo menos o nome da mini.")
                return

            foto_url = upload_storage(
                foto,
                "scanner",
                f"scanner_{usuario.get('id')}"
            )

            cadastrar_mini(
                usuario.get("id"),
                nome,
                marca,
                serie,
                ano,
                raridade,
                valor_pago,
                valor_estimado,
                foto_url,
                "pago",
                "scanner",
                destaque
            )

            try:
                supabase.table("scanner_logs").insert({
                    "usuario_id": usuario.get("id"),
                    "imagem_url": foto_url,
                    "resultado": nome,
                    "confianca": "manual"
                }).execute()
            except Exception:
                pass

            st.success("🔥 Mini cadastrada com segurança pelo Scanner Manual Premium!")


# =========================
# SCANNER INTELIGENTE V2
# =========================
def detectar_sugestoes_ia(nome_arquivo):
    nome = str(nome_arquivo or "").lower()

    marca = "Hot Wheels"
    raridade = "Comum"
    sugestao_nome = ""

    regras = [
        (["kaido", "kh"], "Kaido House"),
        (["minigt", "mini_gt"], "MiniGT"),
        (["tomica"], "Tomica"),
        (["matchbox"], "Matchbox"),
    ]

    for palavras, valor in regras:
        if any(p in nome for p in palavras):
            marca = valor

    if "sth" in nome or "super treasure" in nome:
        raridade = "STH"

    elif "th" in nome:
        raridade = "TH"

    elif "rlc" in nome:
        raridade = "RLC"

    elif "chase" in nome:
        raridade = "Chase"

    elif "premium" in nome:
        raridade = "Premium"

    modelos = {
        "r34": "Nissan Skyline GT-R R34",
        "silvia": "Nissan Silvia",
        "gulf": "Volkswagen Kombi Gulf",
        "supra": "Toyota Supra",
        "f40": "Ferrari F40",
        "lbwk": "Liberty Walk",
    }

    for chave, valor in modelos.items():
        if chave in nome:
            sugestao_nome = valor
            break

    return {
        "marca": marca,
        "raridade": raridade,
        "nome": sugestao_nome
    }




# =========================
# GARAGE PUBLIC SYSTEM V1
# =========================
def gerar_link_publico(usuario):
    username = usuario.get("username_publico")

    if not username:
        username = slugify(usuario.get("nome", "garagehub-user"))

    return f"https://garagehub.app/u/{username}"


def render_public_garage(usuario, minis):
    link_publico = gerar_link_publico(usuario)

    st.markdown(f"""
    <div class="qr-card">
        <h2>🌎 Garagem Pública</h2>

        <p style="color:#cbd5e1;font-weight:800;">
            Compartilhe sua coleção com outros colecionadores.
        </p>

        <div class="qr-box"></div>

        <div class="sidebar-chip">
            🔗 {link_publico}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="feature-grid">

        <div class="feature-card">
            <h3>🏆 Hall da Fama</h3>
            <p>Mostre seus minis favoritos em destaque público.</p>
        </div>

        <div class="feature-card">
            <h3>📸 Perfil Social</h3>
            <p>Compartilhe sua garagem premium com a comunidade.</p>
        </div>

        <div class="feature-card">
            <h3>🚀 QR Code Ready</h3>
            <p>Preparado para QR Code e acesso mobile.</p>
        </div>

    </div>
    """, unsafe_allow_html=True)




# =========================
# CARD INSTALAÇÃO MOBILE
# =========================
def render_card_instalar_app():
    st.markdown("""
    <div class="garagehub-install-card">
        <h3>📱 GarageHub Mobile Mode</h3>
        <p>
            No celular, abra o app pelo navegador e use <b>Adicionar à tela inicial</b>.
            A GarageHub abre com cara de aplicativo, pronta para scanner, garagem e marketplace.
        </p>
    </div>
    """, unsafe_allow_html=True)


# =========================
# FIRST ACCESS SYSTEM
# =========================
def render_primeiro_acesso(usuario):
    st.markdown("""
    <div class="login-shell">
        <div class="login-kicker">🔐 Primeiro acesso</div>
        <h2>Crie sua senha</h2>
        <p>
            Sua conta foi importada para a GarageHub. Defina sua nova senha para continuar.
        </p>
    </div>
    """, unsafe_allow_html=True)

    nova_1 = st.text_input(
        "Nova senha",
        type="password",
        key="primeiro_acesso_senha_1"
    )

    nova_2 = st.text_input(
        "Confirmar senha",
        type="password",
        key="primeiro_acesso_senha_2"
    )

    if st.button("🚀 Ativar acesso", use_container_width=True):

        if len(nova_1) < 4:
            st.error("A senha precisa ter pelo menos 4 caracteres.")
            return False

        if nova_1 != nova_2:
            st.error("As senhas não conferem.")
            return False

        definir_nova_senha(usuario["id"], nova_1)

        usuario["senha"] = nova_1

        st.session_state["usuario"] = usuario

        st.success("🔥 Senha criada com sucesso!")
        st.rerun()

    return False


# =========================
# CSS PREMIUM
# =========================
banner_b64 = img_base64(BANNER_PATH)

st.markdown("""
<style>
:root {
    --bg: #07101f;
    --card: #101827;
    --card2: #0b1220;
    --line: rgba(148, 163, 184, .22);
    --text: #f8fafc;
    --muted: #94a3b8;
    --gold: #facc15;
    --green: #22c55e;
    --red: #ef4444;
    --blue: #38bdf8;
}

.stApp {
    background:
        radial-gradient(circle at top left, rgba(250,204,21,.08), transparent 32%),
        radial-gradient(circle at top right, rgba(56,189,248,.07), transparent 30%),
        linear-gradient(180deg, #07101f, #020617 70%);
    color: var(--text);
}

.main .block-container {
    padding-top: 1.4rem;
    padding-bottom: 3rem;
    max-width: 1280px;
}

h1, h2, h3, h4, p, span, label { color: var(--text); }

label,
.stTextInput label,
.stNumberInput label,
.stSelectbox label,
.stFileUploader label {
    color: #f8fafc !important;
    font-weight: 800 !important;
}

.stTabs [data-baseweb="tab"] {
    color: #cbd5e1 !important;
    font-weight: 900 !important;
    font-size: 15px;
}

.stTabs [aria-selected="true"] { color: var(--gold) !important; }

.stTextInput input,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"] > div {
    background-color: #f8fafc !important;
    color: #111827 !important;
    border-radius: 14px !important;
    border: 1px solid rgba(250,204,21,.35) !important;
    min-height: 44px !important;
}

.stButton > button,
.stFormSubmitButton > button {
    background: linear-gradient(135deg, #facc15, #d97706) !important;
    color: #111827 !important;
    border: none !important;
    border-radius: 14px !important;
    padding: 11px 22px !important;
    font-weight: 950 !important;
    min-width: 150px;
    transition: .25s ease;
    box-shadow: 0 10px 24px rgba(250,204,21,.15);
}

.stButton > button:hover,
.stFormSubmitButton > button:hover {
    transform: translateY(-2px) scale(1.01);
    filter: brightness(1.08);
}

.stFileUploader section {
    background: rgba(15,23,42,.85) !important;
    border: 2px dashed rgba(250,204,21,.65) !important;
    border-radius: 18px !important;
}

.hero {
    background:
        radial-gradient(circle at top left, rgba(250,204,21,.20), transparent 28%),
        linear-gradient(135deg, rgba(15,23,42,.98), rgba(2,6,23,.98));
    border: 1px solid rgba(250,204,21,.26);
    border-radius: 30px;
    padding: 28px;
    margin-bottom: 22px;
    box-shadow: 0 24px 55px rgba(0,0,0,.38);
    overflow: hidden;
}

.hero-img {
    width: 230px;
    height: 150px;
    object-fit: cover;
    border-radius: 24px;
    border: 2px solid var(--gold);
    box-shadow: 0 0 34px rgba(250,204,21,.22);
}

.hero-title {
    font-size: 46px;
    margin: 0;
    line-height: 1;
    color: var(--gold);
    letter-spacing: -1px;
}

.hero-sub { font-size: 18px; color: #cbd5e1; margin: 10px 0 4px; }
.hero-desc { color: #94a3b8; max-width: 760px; }

.metric-card {
    background: linear-gradient(145deg, rgba(15,23,42,.92), rgba(2,6,23,.95));
    border: 1px solid var(--line);
    border-radius: 20px;
    padding: 18px;
    text-align: center;
    min-height: 112px;
    box-shadow: 0 12px 30px rgba(0,0,0,.24);
}
.metric-card h2 { color: var(--gold); margin: 0; font-size: 30px; }
.metric-card p { color: var(--muted); margin: 6px 0 0; font-weight: 800; }

.member-card {
    background:
        radial-gradient(circle at top left, rgba(250,204,21,.18), transparent 34%),
        linear-gradient(135deg, #111827, #020617);
    border: 2px solid rgba(250,204,21,.76);
    border-radius: 30px;
    padding: 30px;
    margin-bottom: 28px;
    box-shadow: 0 0 40px rgba(250,204,21,.16);
}
.member-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 24px;
    margin-bottom: 24px;
    flex-wrap: wrap;
}
.member-top h1 { color: var(--gold); margin: 0; font-size: 38px; }
.member-sub { color: #cbd5e1; margin-top: 4px; font-weight: 800; }

.perfil-avatar-safe {
    width: 124px;
    height: 124px;
    border-radius: 999px;
    overflow: hidden;
    border: 3px solid var(--gold);
    box-shadow: 0 0 26px rgba(250,204,21,.32);
    background: #111827;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #facc15;
    font-size: 44px;
    font-weight: 950;
}
.perfil-avatar-safe img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}
.perfil-avatar-empty {
    background: radial-gradient(circle at 35% 25%, rgba(250,204,21,.18), rgba(15,23,42,.98));
}

.perfil-card-img, .perfil-placeholder {
    width: 124px;
    height: 124px;
    border-radius: 999px;
    object-fit: cover;
    border: 3px solid var(--gold);
    box-shadow: 0 0 26px rgba(250,204,21,.32);
}
.perfil-placeholder {
    background: #1e293b;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 46px;
}
.member-info {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px 22px;
}
.member-info p { font-size: 16px; margin: 0; color: #f8fafc; }
.member-info span { color: var(--gold); font-weight: 950; }
.member-footer {
    margin-top: 28px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 15px;
    flex-wrap: wrap;
}
.member-code, .member-badge {
    padding: 12px 20px;
    border-radius: 16px;
    font-weight: 950;
    font-size: 17px;
}
.member-code { background: var(--gold); color: #111827; letter-spacing: 1px; }
.member-badge { background: linear-gradient(135deg, #16a34a, #22c55e); color: white; }

.garage-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
    margin-top: 16px;
}
.mini-card {
    background:
        radial-gradient(circle at top left, rgba(250,204,21,.10), transparent 35%),
        linear-gradient(160deg, rgba(17,24,39,.98), rgba(2,6,23,.98));
    border: 1px solid rgba(148,163,184,.22);
    border-radius: 24px;
    overflow: hidden;
    min-height: 548px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 18px 42px rgba(0,0,0,.28);
}
.mini-img, .empty-img {
    width: 100%;
    height: 230px;
    object-fit: cover;
    background: #020617;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 54px;
    border-bottom: 1px solid rgba(148,163,184,.18);
}
.mini-body {
    padding: 18px;
    display: flex;
    flex-direction: column;
    flex: 1;
}
.mini-title {
    font-size: 20px;
    font-weight: 950;
    margin: 0 0 8px;
    line-height: 1.2;
    color: #fff;
}
.mini-meta { color: #cbd5e1; font-size: 14px; margin: 3px 0; }
.mini-meta b { color: #f8fafc; }
.price-row {
    margin-top: auto;
    padding-top: 13px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
}
.price-box {
    background: rgba(15,23,42,.86);
    border: 1px solid rgba(148,163,184,.16);
    border-radius: 16px;
    padding: 11px;
}
.price-box small { color: #94a3b8; font-weight: 800; }
.price-box strong { display: block; margin-top: 3px; color: #f8fafc; }
.valor-pos { color: #22c55e !important; }
.valor-neg { color: #ef4444 !important; }
.badge-raridade {
    display: inline-block;
    width: fit-content;
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 950;
    margin: 4px 0 12px;
    color: #111827;
    background: #facc15;
}
.badge-Comum { background: #cbd5e1; }
.badge-TH { background: #22c55e; color:white; }
.badge-STH { background: linear-gradient(135deg, #facc15, #f97316); }
.badge-Premium { background: #38bdf8; }
.badge-RLC { background: #ef4444; color:white; }
.badge-Chase { background: #a855f7; color:white; }
.badge-Especial { background: #fb7185; color:white; }

.admin-pill {
    display:inline-block;
    background:#7f1d1d;
    padding:7px 13px;
    border-radius:999px;
    color:white;
    font-weight:900;
    margin-bottom: 14px;
}
.admin-panel-title {
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:16px;
    margin: 8px 0 18px;
}
.admin-panel-title h2 { margin:0; font-size:30px; }
.admin-panel-title p { margin:4px 0 0; color:var(--muted); font-weight:700; }
.user-card {
    background:
        radial-gradient(circle at top left, rgba(250,204,21,.13), transparent 30%),
        linear-gradient(135deg, rgba(17,24,39,.96), rgba(2,6,23,.98));
    border: 1px solid rgba(250,204,21,.22);
    border-radius: 26px;
    padding: 22px;
    margin: 18px 0 8px;
    box-shadow: 0 18px 42px rgba(0,0,0,.30);
}
.user-card:hover {
    border-color: rgba(250,204,21,.48);
    box-shadow: 0 0 34px rgba(250,204,21,.10), 0 18px 42px rgba(0,0,0,.34);
}
.user-head {
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:14px;
    flex-wrap:wrap;
    margin-bottom:14px;
}
.user-name { font-size:22px; font-weight:950; margin:0; color:#fff; }
.user-email { color:#cbd5e1; font-size:14px; font-weight:800; margin-top:3px; }
.status-pill, .type-pill {
    display:inline-block;
    padding:7px 12px;
    border-radius:999px;
    font-weight:950;
    font-size:12px;
    text-transform:uppercase;
}
.status-ativo { background:rgba(34,197,94,.18); color:#86efac; border:1px solid rgba(34,197,94,.35); }
.status-bloqueado { background:rgba(239,68,68,.16); color:#fca5a5; border:1px solid rgba(239,68,68,.35); }
.type-admin { background:rgba(250,204,21,.16); color:#fde68a; border:1px solid rgba(250,204,21,.34); }
.type-usuario { background:rgba(56,189,248,.14); color:#7dd3fc; border:1px solid rgba(56,189,248,.30); }
.user-info-grid {
    display:grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap:12px;
    margin-top:14px;
}
.user-info-item {
    background:rgba(15,23,42,.72);
    border:1px solid rgba(148,163,184,.14);
    border-radius:16px;
    padding:12px;
    min-height:70px;
}
.user-info-item small {
    display:block;
    color:#94a3b8;
    font-weight:900;
    margin-bottom:5px;
}
.user-info-item strong {
    color:#f8fafc;
    font-weight:900;
    word-break:break-word;
}
.admin-avatar-wrap {
    display:flex;
    align-items:center;
    justify-content:center;
    padding-top:18px;
}
.admin-actions-row {
    margin-top: 0;
}
@media (max-width: 900px) {
    .user-info-grid { grid-template-columns: 1fr; }
}

@media (max-width: 1050px) {
    .garage-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 720px) {
    .garage-grid { grid-template-columns: 1fr; }
    .member-info { grid-template-columns: 1fr; }
    .member-top h1 { font-size: 30px; }
    .hero-title { font-size: 34px; }
    .hero-img { width: 100%; height: 170px; }
    .mini-card { min-height: auto; }
}


/* =========================
   LOGIN / CADASTRO GLASSMORPHISM
   ========================= */
.login-shell {
    width: 100%;
    margin: 22px auto 18px;
    padding: 30px 30px 24px;
    border-radius: 30px;
    background:
        radial-gradient(circle at 12% 0%, rgba(250,204,21,.28), transparent 34%),
        radial-gradient(circle at 90% 20%, rgba(56,189,248,.12), transparent 30%),
        linear-gradient(145deg, rgba(15,23,42,.72), rgba(2,6,23,.86));
    border: 1px solid rgba(250,204,21,.34);
    box-shadow:
        0 26px 70px rgba(0,0,0,.48),
        inset 0 1px 0 rgba(255,255,255,.06),
        0 0 46px rgba(250,204,21,.10);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    position: relative;
    overflow: hidden;
}
.login-shell:before {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(120deg, rgba(255,255,255,.08), transparent 28%, rgba(250,204,21,.06));
    pointer-events: none;
}
.login-kicker {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(250,204,21,.13);
    border: 1px solid rgba(250,204,21,.34);
    color: #fde68a;
    padding: 7px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 950;
    letter-spacing: .4px;
    text-transform: uppercase;
    margin-bottom: 14px;
}
.login-shell h2 {
    margin: 0 0 8px;
    color: #facc15;
    font-size: 34px;
    letter-spacing: -.7px;
}
.login-shell p {
    margin: 0;
    color: #cbd5e1;
    font-weight: 800;
    line-height: 1.45;
}
.login-mini-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin-top: 20px;
}
.login-mini-stat {
    background: rgba(2,6,23,.45);
    border: 1px solid rgba(148,163,184,.16);
    border-radius: 16px;
    padding: 12px;
    text-align: center;
}
.login-mini-stat strong {
    display:block;
    color:#f8fafc;
    font-size:18px;
    font-weight:950;
}
.login-mini-stat small {
    color:#94a3b8;
    font-weight:900;
    font-size:11px;
}
.login-note {
    width: 100%;
    margin: 16px auto 0;
    background: rgba(15,23,42,.74);
    border: 1px solid rgba(56,189,248,.20);
    border-radius: 18px;
    padding: 14px 16px;
    color: #cbd5e1;
    font-weight: 850;
    box-shadow: 0 12px 30px rgba(0,0,0,.24);
}
.login-note b { color: #facc15; }
.login-form-glass {
    margin-top: 0;
}

/* campos com cara de app premium */
.stTextInput input,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"] > div {
    box-shadow: 0 10px 26px rgba(0,0,0,.20) !important;
}

/* tabs centralizadas na tela inicial */
.stTabs [data-baseweb="tab-list"] {
    justify-content: center;
    gap: 12px;
}

.stAlert {
    border-radius: 16px !important;
}

@media (max-width: 720px) {
    .login-shell { padding: 24px 20px; }
    .login-shell h2 { font-size: 28px; }
    .login-mini-stats { grid-template-columns: 1fr; }
}




/* =========================
   CORREÇÃO VISUAL SEGURA - SEM ENCOLHER A PÁGINA
   ========================= */
.main .block-container {
    max-width: 1280px !important;
    padding-top: 1rem !important;
}

.hero {
    margin-top: 4px !important;
    margin-bottom: 18px !important;
    padding: 24px 28px !important;
    border-radius: 28px !important;
}

.hero-img {
    width: 210px !important;
    height: 130px !important;
}

.hero-title {
    font-size: 40px !important;
}

.login-shell {
    max-width: 720px;
    margin: 18px auto 18px !important;
}

.login-note {
    max-width: 720px;
    margin-left: auto !important;
    margin-right: auto !important;
}

/* deixa o login bonito sem apertar tudo */
.login-mini-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
}

/* tabs continuam premium, mas sem criar uma moldura gigante */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(2,6,23,.30);
    width: fit-content;
    margin: 0 auto 16px;
    padding: 6px;
    border: 1px solid rgba(148,163,184,.14);
    border-radius: 999px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 999px !important;
    padding: 8px 14px !important;
}

.stTabs [aria-selected="true"] {
    background: rgba(250,204,21,.14) !important;
    box-shadow: inset 0 0 0 1px rgba(250,204,21,.25);
}

.metric-card, .mini-card, .user-card, .member-card, .login-mini-stat {
    transition: transform .24s ease, box-shadow .24s ease, border-color .24s ease;
}
.metric-card:hover, .mini-card:hover, .user-card:hover, .login-mini-stat:hover {
    transform: translateY(-3px);
    border-color: rgba(250,204,21,.46);
    box-shadow: 0 20px 52px rgba(0,0,0,.36), 0 0 30px rgba(250,204,21,.08);
}

@media (max-width: 720px) {
    .hero-img {
        width: 100% !important;
        height: 160px !important;
    }
    .hero-title {
        font-size: 32px !important;
    }
    .login-shell {
        max-width: 100%;
    }
}


/* =========================
   AJUSTES DE USABILIDADE ADMIN
   ========================= */
.anchor-link, a.anchor-link, .stMarkdown a[href^="#"] {
    display: none !important;
    visibility: hidden !important;
}
.metric-icon {
    width: 54px;
    height: 54px;
    margin: 0 auto 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    background: radial-gradient(circle at 35% 25%, #fde68a, #f59e0b 62%, #78350f);
    color: #020617;
    font-size: 26px;
    font-weight: 950;
    box-shadow: 0 0 24px rgba(250,204,21,.34);
    border: 1px solid rgba(250,204,21,.65);
}
.metric-card h2 { font-size: 38px !important; }
.admin-work-card {
    background: linear-gradient(145deg, rgba(8,47,73,.55), rgba(2,6,23,.94));
    border: 1px solid rgba(34,211,238,.25);
    border-radius: 24px;
    padding: 22px;
    margin: 22px 0 14px;
    box-shadow: 0 18px 44px rgba(0,0,0,.30);
}
.admin-work-card h3 { margin: 0 0 6px; color: #f8fafc; }
.admin-work-card p { margin: 0; color: #bae6fd; font-weight: 800; }
.badge-status, .badge-tipo, .badge-destaque {
    display: inline-block;
    margin: 4px 6px 8px 0;
    padding: 6px 11px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 950;
    text-transform: uppercase;
}
.badge-status-pago { background: rgba(34,197,94,.18); color: #86efac; border: 1px solid rgba(34,197,94,.35); }
.badge-status-pendente { background: rgba(250,204,21,.18); color: #fde68a; border: 1px solid rgba(250,204,21,.35); }
.badge-status-reservado { background: rgba(56,189,248,.18); color: #7dd3fc; border: 1px solid rgba(56,189,248,.35); }
.badge-status-cancelado { background: rgba(239,68,68,.18); color: #fca5a5; border: 1px solid rgba(239,68,68,.35); }
.badge-tipo { background: rgba(168,85,247,.15); color: #d8b4fe; border: 1px solid rgba(168,85,247,.32); }
.badge-destaque { background: rgba(250,204,21,.16); color: #fde68a; border: 1px solid rgba(250,204,21,.38); }


.badge-loja-disponivel { background: rgba(34,197,94,.18); color: #86efac; border: 1px solid rgba(34,197,94,.35); }
.badge-loja-reservado { background: rgba(56,189,248,.18); color: #7dd3fc; border: 1px solid rgba(56,189,248,.35); }
.badge-loja-vendido { background: rgba(239,68,68,.18); color: #fca5a5; border: 1px solid rgba(239,68,68,.35); }
.badge-vip { background: linear-gradient(135deg, #facc15, #f97316); color: #111827; border: 1px solid rgba(250,204,21,.75); }
.badge-comum { background: rgba(56,189,248,.14); color: #7dd3fc; border: 1px solid rgba(56,189,248,.30); }
.store-callout { background: linear-gradient(145deg, rgba(120,53,15,.45), rgba(2,6,23,.94)); border: 1px solid rgba(250,204,21,.28); border-radius: 24px; padding: 20px; margin: 18px 0; box-shadow: 0 18px 44px rgba(0,0,0,.30); }
.store-callout h3 { margin:0 0 6px; color:#facc15; }
.store-callout p { margin:0; color:#fde68a; font-weight:800; }
.badge-pedido-solicitado { background: rgba(250,204,21,.18); color: #fde68a; border: 1px solid rgba(250,204,21,.35); }
.badge-pedido-pendente { background: rgba(250,204,21,.18); color: #fde68a; border: 1px solid rgba(250,204,21,.35); }
.badge-pedido-pago { background: rgba(34,197,94,.18); color: #86efac; border: 1px solid rgba(34,197,94,.35); }
.badge-pedido-reservado { background: rgba(56,189,248,.18); color: #7dd3fc; border: 1px solid rgba(56,189,248,.35); }
.badge-pedido-cancelado { background: rgba(239,68,68,.18); color: #fca5a5; border: 1px solid rgba(239,68,68,.35); }
.badge-pedido-concluido { background: rgba(56,189,248,.18); color: #7dd3fc; border: 1px solid rgba(56,189,248,.35); }



/* =========================
   SUPER UPGRADE — DASHBOARD / HALL / TIMELINE / QR / LAB
   ========================= */
.feature-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px;
    margin: 16px 0 22px;
}
.feature-card {
    background: linear-gradient(145deg, rgba(15,23,42,.92), rgba(2,6,23,.96));
    border: 1px solid rgba(250,204,21,.22);
    border-radius: 24px;
    padding: 20px;
    box-shadow: 0 18px 44px rgba(0,0,0,.30);
}
.feature-card h3 { margin: 0 0 8px; color: #facc15; }
.feature-card p { margin: 0; color: #cbd5e1; font-weight: 800; }
.timeline-item {
    background: rgba(15,23,42,.74);
    border-left: 4px solid #facc15;
    border-radius: 18px;
    padding: 14px 16px;
    margin: 12px 0;
    box-shadow: 0 12px 30px rgba(0,0,0,.22);
}
.timeline-item strong { color: #facc15; }
.qr-card {
    background:
        radial-gradient(circle at top left, rgba(250,204,21,.22), transparent 35%),
        linear-gradient(135deg, rgba(17,24,39,.96), rgba(2,6,23,.98));
    border: 2px solid rgba(250,204,21,.55);
    border-radius: 28px;
    padding: 26px;
    text-align: center;
    box-shadow: 0 0 44px rgba(250,204,21,.14), 0 20px 50px rgba(0,0,0,.34);
}
.qr-box {
    width: 190px;
    height: 190px;
    margin: 18px auto;
    border-radius: 22px;
    background:
        linear-gradient(90deg, #f8fafc 10px, transparent 10px) 0 0/28px 28px,
        linear-gradient(#f8fafc 10px, transparent 10px) 0 0/28px 28px,
        #020617;
    border: 10px solid #f8fafc;
    box-shadow: 0 0 26px rgba(250,204,21,.35);
}
.lab-card {
    background: linear-gradient(145deg, rgba(88,28,135,.50), rgba(2,6,23,.96));
    border: 1px solid rgba(216,180,254,.28);
    border-radius: 24px;
    padding: 20px;
    margin: 14px 0;
}
.lab-card h3 { color: #d8b4fe; margin: 0 0 8px; }
.lab-card p { color: #e9d5ff; font-weight: 800; margin: 0; }
.hall-glow {
    border: 1px solid rgba(250,204,21,.45) !important;
    box-shadow: 0 0 34px rgba(250,204,21,.14), 0 18px 42px rgba(0,0,0,.30) !important;
}
@media (max-width: 900px) {
    .feature-grid { grid-template-columns: 1fr; }
}


/* =========================
   SIDEBAR SAAS PREMIUM — GARAGEHUB
   ========================= */
section[data-testid="stSidebar"] {
    background:
        radial-gradient(circle at top left, rgba(250,204,21,.18), transparent 32%),
        linear-gradient(180deg, #07101f, #020617 78%) !important;
    border-right: 1px solid rgba(250,204,21,.20) !important;
    box-shadow: 18px 0 40px rgba(0,0,0,.22);
}
section[data-testid="stSidebar"] > div {
    padding-top: 1.2rem;
}
.sidebar-brand {
    background:
        radial-gradient(circle at top left, rgba(250,204,21,.18), transparent 35%),
        linear-gradient(145deg, rgba(15,23,42,.92), rgba(2,6,23,.98));
    border: 1px solid rgba(250,204,21,.32);
    border-radius: 22px;
    padding: 16px;
    margin-bottom: 16px;
    box-shadow: 0 18px 42px rgba(0,0,0,.30), 0 0 26px rgba(250,204,21,.06);
}
.sidebar-brand h2 {
    margin: 0;
    font-size: 24px;
    color: #facc15;
    letter-spacing: -.4px;
}
.sidebar-brand p {
    margin: 6px 0 0;
    color: #cbd5e1;
    font-size: 12px;
    font-weight: 800;
    line-height: 1.35;
}
.sidebar-user-card {
    background: rgba(15,23,42,.72);
    border: 1px solid rgba(148,163,184,.16);
    border-radius: 18px;
    padding: 13px;
    margin: 12px 0;
}
.sidebar-user-card strong {
    display: block;
    color: #f8fafc;
    font-weight: 950;
    font-size: 14px;
}
.sidebar-user-card small {
    color: #94a3b8;
    font-weight: 800;
}
.sidebar-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 7px 10px;
    border-radius: 999px;
    margin: 4px 4px 4px 0;
    background: rgba(250,204,21,.13);
    border: 1px solid rgba(250,204,21,.30);
    color: #fde68a;
    font-weight: 950;
    font-size: 11px;
}
.sidebar-section-title {
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: .9px;
    font-size: 11px;
    font-weight: 950;
    margin: 18px 0 8px;
}
.sidebar-menu-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 10px 12px;
    margin: 7px 0;
    border-radius: 15px;
    color: #cbd5e1;
    background: rgba(2,6,23,.34);
    border: 1px solid rgba(148,163,184,.10);
    font-weight: 900;
}
.sidebar-menu-item.active {
    color: #111827;
    background: linear-gradient(135deg, #facc15, #f59e0b);
    border-color: rgba(250,204,21,.72);
    box-shadow: 0 12px 24px rgba(250,204,21,.13);
}
.sidebar-menu-item span:last-child {
    opacity: .75;
    font-size: 11px;
}
.sidebar-footer {
    margin-top: 18px;
    padding: 12px;
    border-radius: 16px;
    background: rgba(2,6,23,.42);
    border: 1px solid rgba(148,163,184,.12);
    color: #94a3b8;
    font-size: 12px;
    font-weight: 800;
    line-height: 1.35;
}
.sidebar-footer b { color: #facc15; }
/* visual premium para radio/menus nativos usados na sidebar */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span {
    color: #e5e7eb !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label {
    background: rgba(15,23,42,.55) !important;
    border: 1px solid rgba(148,163,184,.14) !important;
    border-radius: 14px !important;
    padding: 8px 10px !important;
    margin: 6px 0 !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    border-color: rgba(250,204,21,.42) !important;
    background: rgba(250,204,21,.08) !important;
}



/* =========================
   MARKETPLACE PREMIUM — VITRINE CINEMATOGRÁFICA
   ========================= */
.market-hero {
    background:
        radial-gradient(circle at 10% 20%, rgba(250,204,21,.24), transparent 30%),
        radial-gradient(circle at 90% 10%, rgba(56,189,248,.16), transparent 28%),
        linear-gradient(135deg, rgba(15,23,42,.96), rgba(2,6,23,.98));
    border: 1px solid rgba(250,204,21,.36);
    border-radius: 30px;
    padding: 28px;
    margin: 18px 0 22px;
    box-shadow: 0 26px 70px rgba(0,0,0,.42), 0 0 42px rgba(250,204,21,.09);
    position: relative;
    overflow: hidden;
}
.market-hero:after {
    content: "";
    position:absolute;
    inset:0;
    background: linear-gradient(120deg, rgba(255,255,255,.08), transparent 30%, rgba(250,204,21,.05));
    pointer-events:none;
}
.market-kicker {
    display:inline-flex;
    padding: 8px 13px;
    border-radius:999px;
    background: rgba(250,204,21,.15);
    border:1px solid rgba(250,204,21,.34);
    color:#fde68a;
    font-size:12px;
    font-weight:950;
    text-transform:uppercase;
    letter-spacing:.4px;
    margin-bottom:12px;
}
.market-title {
    margin:0;
    color:#facc15;
    font-size:42px;
    line-height:1.05;
    letter-spacing:-.8px;
}
.market-desc {
    color:#cbd5e1;
    margin:10px 0 0;
    font-weight:800;
    max-width:820px;
}
.market-stats {
    display:grid;
    grid-template-columns: repeat(3, minmax(0,1fr));
    gap:12px;
    margin-top:20px;
}
.market-stat {
    background:rgba(2,6,23,.50);
    border:1px solid rgba(148,163,184,.16);
    border-radius:18px;
    padding:14px;
    text-align:center;
}
.market-stat strong { display:block; color:#f8fafc; font-size:20px; font-weight:950; }
.market-stat small { color:#94a3b8; font-weight:900; }
.market-card {
    display:grid;
    grid-template-columns: 300px minmax(0, 1fr);
    gap:22px;

    background:
        radial-gradient(circle at top left, rgba(250,204,21,.16), transparent 34%),
        linear-gradient(160deg, rgba(17,24,39,.98), rgba(2,6,23,.99));

    border:1px solid rgba(250,204,21,.28);
    border-radius:30px;
    overflow:hidden;
    margin-bottom:22px;
    padding:22px;

    box-shadow:
        0 22px 58px rgba(0,0,0,.40),
        0 0 34px rgba(250,204,21,.07);

    transition:.25s ease;
}
.market-card:hover {
    transform: translateY(-4px);
    border-color: rgba(250,204,21,.60);
    box-shadow:
        0 28px 76px rgba(0,0,0,.50),
        0 0 40px rgba(250,204,21,.14);
}
.market-img,
.market-empty {
    width:100%;
    height:300px;
    object-fit:cover;
    object-position:center;
    background:#020617;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:58px;
    border:1px solid rgba(148,163,184,.18);
    border-radius:24px;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.03), 0 16px 34px rgba(0,0,0,.32);
}
.market-body {
    padding:4px 2px;
    display:flex;
    flex-direction:column;
    min-width:0;
}
.market-name {
    margin:0 0 8px;
    color:#fff;
    font-size:30px;
    font-weight:950;
    line-height:1.08;
    letter-spacing:-.45px;
}
.market-line {
    color:#cbd5e1;
    font-size:15px;
    font-weight:850;
    margin:4px 0;
}
.market-price-grid {
    display:grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap:12px;
    margin-top:auto;
    padding-top:16px;
}
.market-price {
    margin-top:0;
    padding:15px;
    background:rgba(15,23,42,.82);
    border:1px solid rgba(148,163,184,.16);
    border-radius:18px;
}
.market-price small {
    color:#94a3b8;
    font-weight:900;
    font-size:12px;
}
.market-price strong {
    display:block;
    margin-top:5px;
    color:#facc15;
    font-size:24px;
    font-weight:950;
    word-break:break-word;
}
.market-tags { margin: 8px 0 12px; }
.market-tag {
    display:inline-block;
    margin:4px 5px 4px 0;
    padding:7px 11px;
    border-radius:999px;
    font-size:11px;
    font-weight:950;
    text-transform:uppercase;
}
.market-tag-gold { background:rgba(250,204,21,.18); color:#fde68a; border:1px solid rgba(250,204,21,.35); }
.market-tag-vip { background:linear-gradient(135deg,#facc15,#f97316); color:#111827; border:1px solid rgba(250,204,21,.70); }
.market-tag-rare { background:rgba(168,85,247,.18); color:#d8b4fe; border:1px solid rgba(168,85,247,.35); }
.market-tag-ok { background:rgba(34,197,94,.18); color:#86efac; border:1px solid rgba(34,197,94,.35); }
.market-filter-box {
    background:rgba(15,23,42,.72);
    border:1px solid rgba(148,163,184,.14);
    border-radius:22px;
    padding:16px;
    margin: 14px 0 20px;
}
.favorite-chip {
    align-self:flex-end;
    font-size:20px;
    filter: drop-shadow(0 0 10px rgba(239,68,68,.35));
}
@media (max-width: 1100px) {
    .market-card { grid-template-columns: 240px minmax(0, 1fr); }
    .market-img, .market-empty { height:260px; }
    .market-name { font-size:26px; }
    .market-price-grid { grid-template-columns:1fr; }
}
@media (max-width: 760px) {
    .market-stats { grid-template-columns:1fr; }
    .market-title { font-size:32px; }
    .market-card { grid-template-columns:1fr; padding:18px; }
    .market-img, .market-empty { height:280px; }
    .market-name { font-size:25px; }
}



/* =========================
   PIX ASSISTIDO — CHECKOUT MANUAL PREMIUM
   ========================= */
.pix-card {
    background:
        radial-gradient(circle at top left, rgba(34,197,94,.18), transparent 32%),
        linear-gradient(145deg, rgba(15,23,42,.95), rgba(2,6,23,.98));
    border: 1px solid rgba(34,197,94,.35);
    border-radius: 24px;
    padding: 18px;
    margin: 14px 0 18px;
    box-shadow: 0 18px 44px rgba(0,0,0,.30), 0 0 30px rgba(34,197,94,.08);
}
.pix-head { display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap; }
.pix-kicker {
    display:inline-flex;
    padding: 6px 10px;
    border-radius:999px;
    background:rgba(34,197,94,.16);
    border:1px solid rgba(34,197,94,.35);
    color:#86efac;
    font-size:11px;
    font-weight:950;
    text-transform:uppercase;
}
.pix-card h3 { margin:8px 0 4px; color:#86efac; }
.pix-card p { margin:0; color:#cbd5e1; font-weight:800; }
.pix-card b { color:#f8fafc; }
.pix-fake-qr {
    width: 96px;
    height: 96px;
    border-radius: 16px;
    background:
        linear-gradient(90deg, #f8fafc 8px, transparent 8px) 0 0/22px 22px,
        linear-gradient(#f8fafc 8px, transparent 8px) 0 0/22px 22px,
        #020617;
    border: 7px solid #f8fafc;
    box-shadow: 0 0 22px rgba(34,197,94,.28);
}
.pix-code {
    margin-top:14px;
    background:rgba(2,6,23,.65);
    border:1px solid rgba(148,163,184,.18);
    border-radius:16px;
    padding:12px;
    overflow-wrap:anywhere;
}
.pix-code code { color:#86efac; font-weight:900; }
.pix-help { margin-top:10px !important; color:#94a3b8 !important; font-size:13px; }
.badge-pedido-aguardando_pix { background: rgba(34,197,94,.18); color: #86efac; border: 1px solid rgba(34,197,94,.35); }


/* =========================
   PRO PACK FINAL — CHECKOUT / CARRINHO / PERFIL / NOTIFICAÇÕES / MOBILE / EXECUTIVO
   ========================= */
.pro-grid { display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:16px; margin:18px 0; }
.pro-card { background: linear-gradient(145deg, rgba(15,23,42,.92), rgba(2,6,23,.98)); border: 1px solid rgba(250,204,21,.22); border-radius: 24px; padding: 20px; box-shadow: 0 18px 44px rgba(0,0,0,.30); }
.pro-card h3 { margin:0 0 8px; color:#facc15; }
.pro-card p { margin:0; color:#cbd5e1; font-weight:800; }
.pro-card strong { color:#f8fafc; }
.pro-hero { background: radial-gradient(circle at top left, rgba(250,204,21,.22), transparent 35%), radial-gradient(circle at bottom right, rgba(56,189,248,.12), transparent 32%), linear-gradient(135deg, rgba(15,23,42,.96), rgba(2,6,23,.98)); border:1px solid rgba(250,204,21,.34); border-radius:30px; padding:26px; margin:18px 0; box-shadow:0 26px 70px rgba(0,0,0,.42), 0 0 42px rgba(250,204,21,.08); }
.pro-hero h2 { margin:0 0 8px; color:#facc15; font-size:34px; }
.pro-hero p { margin:0; color:#cbd5e1; font-weight:850; }
.notify-item { background: rgba(15,23,42,.72); border:1px solid rgba(148,163,184,.14); border-left:4px solid #facc15; border-radius:18px; padding:14px 16px; margin:10px 0; }
.notify-item strong { color:#facc15; }
.checkout-box { background: linear-gradient(145deg, rgba(20,83,45,.42), rgba(2,6,23,.95)); border:1px solid rgba(34,197,94,.30); border-radius:24px; padding:18px; margin:14px 0; }
.checkout-box h3 { color:#86efac; margin:0 0 8px; }
.profile-banner { background: radial-gradient(circle at 20% 15%, rgba(250,204,21,.24), transparent 28%), linear-gradient(135deg, rgba(17,24,39,.96), rgba(2,6,23,.98)); border:2px solid rgba(250,204,21,.45); border-radius:30px; padding:26px; box-shadow:0 0 40px rgba(250,204,21,.12), 0 20px 50px rgba(0,0,0,.34); }
.profile-banner h2 { color:#facc15; margin:0; }
.mobile-preview { max-width:360px; margin:18px auto; border:10px solid rgba(15,23,42,.90); border-radius:36px; background:#020617; box-shadow:0 26px 70px rgba(0,0,0,.48), 0 0 42px rgba(250,204,21,.10); overflow:hidden; }
.mobile-top { padding:18px; background:linear-gradient(135deg,#111827,#020617); border-bottom:1px solid rgba(250,204,21,.20); }
.mobile-top h3 { margin:0; color:#facc15; }
.mobile-body { padding:16px; }
.mobile-nav { display:grid; grid-template-columns:repeat(4,1fr); gap:6px; padding:10px; background:rgba(15,23,42,.82); }
.mobile-nav span { text-align:center; color:#cbd5e1; font-size:11px; font-weight:900; }
.cart-row { display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; background:rgba(15,23,42,.72); border:1px solid rgba(148,163,184,.14); border-radius:18px; padding:14px; margin:10px 0; }
.cart-row strong { color:#f8fafc; }
@media (max-width: 900px) { .pro-grid { grid-template-columns: 1fr; } }


/* =========================
   SCANNER IA LAB — CAPTURA REAL ASSISTIDA
   ========================= */
.scanner-hero {
    background:
        radial-gradient(circle at top left, rgba(168,85,247,.24), transparent 34%),
        radial-gradient(circle at bottom right, rgba(56,189,248,.14), transparent 32%),
        linear-gradient(135deg, rgba(15,23,42,.96), rgba(2,6,23,.98));
    border: 1px solid rgba(216,180,254,.32);
    border-radius: 30px;
    padding: 26px;
    margin: 18px 0;
    box-shadow: 0 26px 70px rgba(0,0,0,.42), 0 0 42px rgba(168,85,247,.10);
}
.scanner-kicker {
    display:inline-flex;
    padding: 8px 13px;
    border-radius:999px;
    background: rgba(168,85,247,.18);
    border:1px solid rgba(216,180,254,.34);
    color:#e9d5ff;
    font-size:12px;
    font-weight:950;
    text-transform:uppercase;
    letter-spacing:.4px;
    margin-bottom:12px;
}
.scanner-hero h2 { margin:0 0 8px; color:#d8b4fe; font-size:36px; }
.scanner-hero p { margin:0; color:#e9d5ff; font-weight:850; }
.scanner-step {
    background: linear-gradient(145deg, rgba(88,28,135,.42), rgba(2,6,23,.96));
    border: 1px solid rgba(216,180,254,.25);
    border-radius: 24px;
    padding: 18px;
    box-shadow: 0 18px 44px rgba(0,0,0,.28);
}
.scanner-step h3 { color:#d8b4fe; margin:0 0 8px; }
.scanner-step p { color:#e9d5ff; font-weight:800; margin:0; }
.scanner-result {
    background:
        radial-gradient(circle at top left, rgba(250,204,21,.20), transparent 35%),
        linear-gradient(145deg, rgba(15,23,42,.95), rgba(2,6,23,.98));
    border: 1px solid rgba(250,204,21,.36);
    border-radius: 24px;
    padding: 20px;
    margin: 18px 0;
    box-shadow: 0 18px 44px rgba(0,0,0,.30), 0 0 30px rgba(250,204,21,.08);
}
.scanner-result h3 { color:#facc15; margin:0 0 8px; }
.scanner-result p { color:#cbd5e1; font-weight:850; margin:4px 0; }
.scanner-score {
    float:right;
    width:64px;
    height:64px;
    display:flex;
    align-items:center;
    justify-content:center;
    border-radius:999px;
    color:#111827;
    background:linear-gradient(135deg,#facc15,#f97316);
    font-weight:950;
    box-shadow:0 0 22px rgba(250,204,21,.28);
}


/* =========================
   EXPANDER PREMIUM — CORREÇÃO BARRA BRANCA
   ========================= */
div[data-testid="stExpander"] {
    background:
        linear-gradient(145deg, rgba(15,23,42,.96), rgba(2,6,23,.98)) !important;
    border: 1px solid rgba(250,204,21,.24) !important;
    border-radius: 18px !important;
    overflow: hidden !important;
    margin-bottom: 20px !important;
    box-shadow:
        0 18px 44px rgba(0,0,0,.30),
        0 0 24px rgba(250,204,21,.06) !important;
}

div[data-testid="stExpander"] details {
    background: transparent !important;
}

div[data-testid="stExpander"] summary {
    background:
        linear-gradient(145deg, rgba(15,23,42,.92), rgba(2,6,23,.98)) !important;
    color: #f8fafc !important;
    border-radius: 18px !important;
    padding: 12px 18px !important;
    transition: .25s ease !important;
}

div[data-testid="stExpander"] summary:hover {
    background:
        linear-gradient(145deg, rgba(250,204,21,.10), rgba(2,6,23,.98)) !important;
}

div[data-testid="stExpander"] summary p,
div[data-testid="stExpander"] summary span,
div[data-testid="stExpander"] summary div {
    color: #f8fafc !important;
    font-weight: 900 !important;
}

div[data-testid="stExpander"] svg {
    color: #facc15 !important;
    fill: #facc15 !important;
}

div[data-testid="stExpander"] div[data-testid="stExpanderDetails"] {
    background: rgba(2,6,23,.35) !important;
    color: #f8fafc !important;
}



/* =========================
   FIX MOBILE NAV/TABS SCROLL
   ========================= */
@media (max-width: 768px) {

    .stTabs [data-baseweb="tab-list"],
    div[role="tablist"],
    .tabs,
    .nav-tabs,
    .tab-menu {
        width: 100% !important;
        max-width: 100vw !important;

        display: flex !important;
        flex-wrap: nowrap !important;

        overflow-x: auto !important;
        overflow-y: hidden !important;

        white-space: nowrap !important;
        scrollbar-width: none !important;
        -ms-overflow-style: none !important;

        justify-content: flex-start !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        padding: 6px 6px 10px 6px !important;

        box-sizing: border-box !important;
    }

    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar,
    div[role="tablist"]::-webkit-scrollbar,
    .tabs::-webkit-scrollbar,
    .nav-tabs::-webkit-scrollbar,
    .tab-menu::-webkit-scrollbar {
        display: none !important;
    }

    .stTabs [data-baseweb="tab"],
    button[role="tab"] {
        flex: 0 0 auto !important;
        min-width: max-content !important;
        max-width: none !important;
        white-space: nowrap !important;
        padding: 8px 14px !important;
    }

    .stTabs {
        max-width: 100vw !important;
        overflow: hidden !important;
    }

    .main .block-container {
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }

    html,
    body,
    .stApp {
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }
}



/* =========================
   MINHA GARAGEM — FOTO CONTROLADA EM CARD
   ========================= */
.garage-photo-box {
    width: 100% !important;
    height: 190px !important;
    max-height: 190px !important;
    background: #020617 !important;
    border: 1px solid rgba(148,163,184,.18) !important;
    border-radius: 18px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    overflow: hidden !important;
    margin-bottom: 12px !important;
}

.garage-photo-box img {
    width: 100% !important;
    height: 100% !important;
    max-height: 190px !important;
    object-fit: contain !important;
    object-position: center !important;
    display: block !important;
}

.garage-empty {
    font-size: 54px !important;
}

@media (max-width: 720px) {
    .garage-photo-box {
        height: 170px !important;
        max-height: 170px !important;
    }

    .garage-photo-box img {
        max-height: 170px !important;
    }
}



/* =========================
   ADMIN GARAGEM CLIENTE
   ========================= */
.garage-photo-box {
    width: 100% !important;
    height: 190px !important;
    max-height: 190px !important;
    background: #020617 !important;
    border: 1px solid rgba(148,163,184,.18) !important;
    border-radius: 18px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    overflow: hidden !important;
    margin-bottom: 12px !important;
}
.garage-photo-box img {
    width: 100% !important;
    height: 100% !important;
    max-height: 190px !important;
    object-fit: contain !important;
    object-position: center !important;
    display: block !important;
}
.garage-empty { font-size: 54px !important; }



/* =========================
   CARD FINANCEIRO — PENDENTES
   ========================= */
.metric-pendente {
    border-color: rgba(250,204,21,.45) !important;
    background:
        radial-gradient(circle at top left, rgba(250,204,21,.18), transparent 34%),
        linear-gradient(145deg, rgba(120,53,15,.38), rgba(2,6,23,.96)) !important;
}

.metric-pendente small {
    display: block;
    margin-top: 6px;
    color: #fde68a;
    font-weight: 950;
    font-size: 13px;
}

@media (max-width: 900px) {
    .metric-card h2 {
        font-size: 26px !important;
    }
}


/* =========================
   RIFAS — GRADE VISUAL DOS NÚMEROS
   ========================= */
.rifa-grid-card {
    background:
        radial-gradient(circle at top left, rgba(56,189,248,.12), transparent 32%),
        linear-gradient(145deg, rgba(15,23,42,.94), rgba(2,6,23,.98));
    border: 1px solid rgba(250,204,21,.28);
    border-radius: 24px;
    padding: 18px;
    margin: 16px 0 22px;
    box-shadow: 0 18px 44px rgba(0,0,0,.30), 0 0 30px rgba(250,204,21,.07);
}
.rifa-grid-head {
    display:flex;
    align-items:flex-start;
    justify-content:space-between;
    gap:14px;
    flex-wrap:wrap;
    margin-bottom:14px;
}
.rifa-grid-head h3 {
    margin:0 0 4px;
    color:#facc15;
    font-size:24px;
}
.rifa-grid-head p {
    margin:0;
    color:#cbd5e1;
    font-weight:800;
}
.rifa-legenda {
    display:flex;
    gap:8px;
    flex-wrap:wrap;
    align-items:center;
}
.rifa-legenda span {
    display:inline-flex;
    align-items:center;
    gap:6px;
    padding:7px 10px;
    border-radius:999px;
    font-size:11px;
    font-weight:950;
    border:1px solid rgba(148,163,184,.20);
    background:rgba(15,23,42,.70);
    color:#e5e7eb;
}
.rifa-dot {
    width:11px;
    height:11px;
    border-radius:999px;
    display:inline-block;
}
.rifa-dot.disponivel { background:#38bdf8; }
.rifa-dot.pago { background:#22c55e; }
.rifa-dot.pendente { background:#facc15; }
.rifa-dot.vencedor { background:#ef4444; }
.rifa-grid {
    display:grid;
    grid-template-columns: repeat(auto-fill, minmax(54px, 1fr));
    gap:8px;
}
.rifa-num {
    min-height:46px;
    border-radius:14px;
    display:flex;
    align-items:center;
    justify-content:center;
    font-weight:950;
    font-size:13px;
    letter-spacing:.3px;
    border:1px solid rgba(255,255,255,.09);
    box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 8px 18px rgba(0,0,0,.20);
    transition:.20s ease;
}
.rifa-num:hover {
    transform: translateY(-2px) scale(1.03);
    filter:brightness(1.08);
}
.rifa-num-disponivel {
    background:rgba(56,189,248,.13);
    color:#7dd3fc;
    border-color:rgba(56,189,248,.35);
}
.rifa-num-pago {
    background:rgba(34,197,94,.16);
    color:#86efac;
    border-color:rgba(34,197,94,.42);
}
.rifa-num-pendente,
.rifa-num-reservado {
    background:rgba(250,204,21,.16);
    color:#fde68a;
    border-color:rgba(250,204,21,.45);
}
.rifa-num-vencedor {
    background:linear-gradient(135deg, #ef4444, #991b1b);
    color:#fff;
    border-color:rgba(248,113,113,.75);
    box-shadow:0 0 26px rgba(239,68,68,.35), 0 10px 24px rgba(0,0,0,.26);
}
@media (max-width: 720px) {
    .rifa-grid {
        grid-template-columns: repeat(auto-fill, minmax(44px, 1fr));
        gap:6px;
    }
    .rifa-num {
        min-height:40px;
        font-size:12px;
        border-radius:12px;
    }
}


/* =========================
   GAMIFICAÇÃO GARAGEHUB V11
   ========================= */
.badge-vip {
    display:inline-block;
    margin:4px 6px 8px 0;
    padding:7px 12px;
    border-radius:999px;
    font-size:11px;
    font-weight:950;
    text-transform:uppercase;
    background:linear-gradient(135deg,#facc15,#f97316);
    color:#111827;
    border:1px solid rgba(250,204,21,.75);
}
.user-card .badge-destaque {
    box-shadow:0 0 18px rgba(250,204,21,.08);
}

</style>
""", unsafe_allow_html=True)




# =========================
# SIDEBAR SAAS PREMIUM
# =========================
def render_sidebar_saas(usuario):
    """Sidebar visual premium para deixar o app com cara de SaaS sem quebrar as abas existentes."""
    nome = html.escape(str(usuario.get("nome", "Usuário") or "Usuário"))
    tipo = str(usuario.get("tipo", "usuario") or "usuario")
    nivel = str(usuario.get("nivel_cliente", "comum") or "comum")
    codigo = html.escape(str(usuario.get("codigo_membro", "") or "-"))

    perfil = "ADMIN" if tipo == "admin" else ("VIP" if nivel == "vip" else "CLIENTE")
    perfil_icon = "👑" if tipo == "admin" else ("💎" if nivel == "vip" else "🏁")

    with st.sidebar:
        st.markdown("""
        <div class="sidebar-brand">
            <h2>🏁 GarageHub</h2>
            <p>Garagem digital, loja, pedidos, VIP, ranking e comunidade de colecionadores.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="sidebar-user-card">
            <strong>{perfil_icon} {nome}</strong>
            <small>{perfil} • Carteirinha {codigo}</small><br>
            <span class="sidebar-chip">{perfil_icon} {perfil}</span>
            <span class="sidebar-chip">1:64</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="sidebar-section-title">Navegação</div>', unsafe_allow_html=True)

        if tipo == "admin":
            st.markdown("""
            <div class="sidebar-menu-item active"><span>📊 Dashboard Admin</span><span>online</span></div>
            <div class="sidebar-menu-item"><span>👥 Clientes</span><span>CRM</span></div>
            <div class="sidebar-menu-item"><span>🛒 Loja</span><span>vendas</span></div>
            <div class="sidebar-menu-item"><span>💰 Pedidos</span><span>fluxo</span></div>
            <div class="sidebar-menu-item"><span>🏎️ Minis</span><span>acervo</span></div>
            <div class="sidebar-menu-item"><span>🏆 Hall / Ranking</span><span>vip</span></div>
            <div class="sidebar-menu-item"><span>🧪 Lab IA/Pix</span><span>beta</span></div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="sidebar-menu-item active"><span>🏠 Minha área</span><span>online</span></div>
            <div class="sidebar-menu-item"><span>🏎️ Minha garagem</span><span>coleção</span></div>
            <div class="sidebar-menu-item"><span>🛒 Loja</span><span>comprar</span></div>
            <div class="sidebar-menu-item"><span>📦 Meus pedidos</span><span>status</span></div>
            <div class="sidebar-menu-item"><span>🎫 Carteirinha</span><span>QR</span></div>
            <div class="sidebar-menu-item"><span>🏆 Hall da Fama</span><span>ranking</span></div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div class="sidebar-footer">
            <b>GarageHub SaaS Mode</b><br>
            Use as abas do painel principal para acessar cada módulo. A estrutura lateral deixa a navegação com cara de plataforma profissional.
        </div>
        """, unsafe_allow_html=True)



# =========================
# PRO PACK FINAL — FUNÇÕES SEGURAS
# =========================
def status_label(status):
    mapa = {
        "solicitado": "Solicitado", "pendente": "Pendente", "reservado": "Reservado",
        "aguardando_pix": "Aguardando Pix", "pago": "Pago", "concluido": "Concluído", "cancelado": "Cancelado",
    }
    return mapa.get(str(status or "").lower(), str(status or "-").title())


def calcular_ranking(clientes, minis):
    ranking = []
    for c in clientes:
        cid = c.get("id")
        minis_cliente = [m for m in minis if m.get("usuario_id") == cid]
        total_pago = sum(float(m.get("valor_pago") or 0) for m in minis_cliente if (m.get("status_pagamento") or "") == "pago")
        valor_estimado = sum(float(m.get("valor_estimado") or 0) for m in minis_cliente)
        raras = len([m for m in minis_cliente if (m.get("raridade") or "") in ["TH", "STH", "RLC", "Chase", "Especial"]])
        ranking.append({"cliente": c, "qtd": len(minis_cliente), "total_pago": total_pago, "valor_estimado": valor_estimado, "raras": raras})
    return sorted(ranking, key=lambda x: (x["total_pago"], x["qtd"], x["raras"]), reverse=True)


# =========================
# GAMIFICAÇÃO GARAGEHUB V11
# =========================
def safe_float(valor):
    try:
        return float(valor or 0)
    except Exception:
        return 0.0


def nivel_gamificacao(pontos):
    pontos = int(pontos or 0)
    if pontos >= 10000:
        return "💎 Diamante", "Diamante"
    if pontos >= 3000:
        return "🥇 Ouro", "Ouro"
    if pontos >= 1000:
        return "🥈 Prata", "Prata"
    return "🥉 Bronze", "Bronze"


def proximo_nivel_info(pontos):
    pontos = int(pontos or 0)
    metas = [(1000, "Prata"), (3000, "Ouro"), (10000, "Diamante")]
    for meta, nome in metas:
        if pontos < meta:
            faltam = meta - pontos
            progresso = int((pontos / meta) * 100) if meta else 0
            return nome, faltam, min(progresso, 100)
    return "Topo", 0, 100


def calcular_gamificacao_clientes(clientes, minis, rifas=None, rifa_numeros=None):
    # Ranking unificado: compras + coleção + raridades + rifas + vitórias.
    rifas = rifas or []
    rifa_numeros = rifa_numeros or []
    resultado = []

    vitorias_por_cliente = {}
    for r in rifas:
        if str(r.get("status") or "").lower() != "sorteada":
            continue
        for campo in ["vencedor_usuario_id", "top_comprador_usuario_id", "top_ganhador_usuario_id"]:
            uid = str(r.get(campo) or "").strip()
            if uid and uid.lower() not in ["none", "null", ""]:
                vitorias_por_cliente[uid] = vitorias_por_cliente.get(uid, 0) + 1

    cotas_por_cliente = {}
    valor_rifas_por_cliente = {}
    rifas_por_id = {str(r.get("id")): r for r in rifas}
    for n in rifa_numeros:
        uid = str(n.get("usuario_id") or "").strip()
        if not uid:
            continue
        cotas_por_cliente[uid] = cotas_por_cliente.get(uid, 0) + 1
        rifa = rifas_por_id.get(str(n.get("rifa_id") or ""), {})
        valor_rifas_por_cliente[uid] = valor_rifas_por_cliente.get(uid, 0.0) + safe_float(rifa.get("valor_numero"))

    for c in clientes or []:
        uid = str(c.get("id") or "")
        minis_cliente = [m for m in (minis or []) if str(m.get("usuario_id")) == uid]
        minis_pagas = [m for m in minis_cliente if str(m.get("status_pagamento") or "").lower() == "pago"]
        total_pago = sum(safe_float(m.get("valor_pago")) for m in minis_pagas)
        valor_estimado = sum(safe_float(m.get("valor_estimado")) for m in minis_cliente)
        raras = len([m for m in minis_cliente if str(m.get("raridade") or "") in ["TH", "STH", "RLC", "Chase", "Especial", "Premium"]])
        vitorias = vitorias_por_cliente.get(uid, 0)
        cotas = cotas_por_cliente.get(uid, 0)
        valor_rifas = valor_rifas_por_cliente.get(uid, 0.0)

        pontos = int(
            total_pago * 5 +
            valor_estimado * 1 +
            len(minis_cliente) * 35 +
            raras * 250 +
            cotas * 20 +
            vitorias * 1000
        )
        nivel_label, nivel_nome = nivel_gamificacao(pontos)
        prox_nome, faltam, progresso = proximo_nivel_info(pontos)

        conquistas = []
        if len(minis_cliente) >= 1:
            conquistas.append("🏁 Primeira garagem")
        if len(minis_cliente) >= 10:
            conquistas.append("🚗 Colecionador 10+")
        if raras >= 1:
            conquistas.append("💎 Caçador de raras")
        if cotas >= 10:
            conquistas.append("🎟️ 10 cotas em rifas")
        if cotas >= 50:
            conquistas.append("🔥 Rei das cotas")
        if vitorias >= 1:
            conquistas.append("🏆 Primeira vitória")
        if vitorias >= 3:
            conquistas.append("👑 Lenda das rifas")
        if total_pago >= 1000:
            conquistas.append("💰 Cliente Elite")

        resultado.append({
            "cliente": c,
            "pontos": pontos,
            "nivel_label": nivel_label,
            "nivel_nome": nivel_nome,
            "proximo_nivel": prox_nome,
            "faltam": faltam,
            "progresso": progresso,
            "minis": len(minis_cliente),
            "minis_pagas": len(minis_pagas),
            "total_pago": total_pago,
            "valor_estimado": valor_estimado,
            "raras": raras,
            "cotas": cotas,
            "valor_rifas": valor_rifas,
            "vitorias": vitorias,
            "conquistas": conquistas,
        })

    return sorted(resultado, key=lambda x: (x["pontos"], x["vitorias"], x["cotas"], x["total_pago"]), reverse=True)


def buscar_todos_numeros_rifas():
    try:
        return supabase.table("rifa_numeros").select("*").execute().data
    except Exception:
        return []


def render_card_gamificacao(item, pos=None, destaque_voce=False):
    c = item.get("cliente") or {}
    nome = html.escape(str(c.get("nome") or "Cliente"))
    email = html.escape(str(c.get("email") or "-"))
    titulo_pos = f"#{pos} — " if pos else ""
    voce = " • VOCÊ" if destaque_voce else ""
    conquistas = item.get("conquistas") or []
    conquistas_html = "".join([f'<span class="badge-destaque">{html.escape(x)}</span>' for x in conquistas[:6]]) or '<span class="badge-destaque">Em evolução</span>'

    st.markdown(f'''
    <div class="user-card hall-glow">
        <div class="user-head">
            <div>
                <div class="user-name">{titulo_pos}{nome}{voce}</div>
                <div class="user-email">{email}</div>
            </div>
            <div>
                <span class="badge-vip">{html.escape(item.get("nivel_label") or "Bronze")}</span>
                <span class="badge-destaque">{int(item.get("pontos") or 0)} pts</span>
            </div>
        </div>
        <div class="user-info-grid">
            <div class="user-info-item"><small>Compras pagas</small><strong>{money(item.get('total_pago') or 0)}</strong></div>
            <div class="user-info-item"><small>Cotas em rifas</small><strong>{item.get('cotas') or 0}</strong></div>
            <div class="user-info-item"><small>Vitórias</small><strong>{item.get('vitorias') or 0}</strong></div>
            <div class="user-info-item"><small>Minis na garagem</small><strong>{item.get('minis') or 0}</strong></div>
            <div class="user-info-item"><small>Raras / Premium</small><strong>{item.get('raras') or 0}</strong></div>
            <div class="user-info-item"><small>Próximo nível</small><strong>{html.escape(str(item.get('proximo_nivel') or '-'))}</strong></div>
        </div>
        <div style="margin-top:14px;">{conquistas_html}</div>
    </div>
    ''', unsafe_allow_html=True)

    progresso = int(item.get("progresso") or 0)
    if item.get("faltam", 0) > 0:
        st.progress(progresso, text=f"{progresso}% para {item.get('proximo_nivel')} — faltam {item.get('faltam')} pontos")
    else:
        st.progress(100, text="Nível máximo alcançado — Diamante")


def render_gamificacao_admin(clientes, minis):
    st.markdown('''
    <div class="pro-hero">
        <h2>🎮 Gamificação GarageHub</h2>
        <p>Ranking premium com pontos, níveis, conquistas, cotas de rifas, vitórias e compras pagas.</p>
    </div>
    ''', unsafe_allow_html=True)

    try:
        rifas_rank = buscar_rifas()
    except Exception:
        rifas_rank = []
    rifa_numeros_rank = buscar_todos_numeros_rifas()
    ranking = calcular_gamificacao_clientes(clientes, minis, rifas_rank, rifa_numeros_rank)

    if not ranking:
        st.info("Ainda não há dados suficientes para a gamificação.")
        return

    total_pontos = sum(int(i.get("pontos") or 0) for i in ranking)
    total_cotas = sum(int(i.get("cotas") or 0) for i in ranking)
    total_vitorias = sum(int(i.get("vitorias") or 0) for i in ranking)

    a, b, c = st.columns(3)
    with a:
        st.markdown(f'<div class="metric-card"><div class="metric-icon">⭐</div><h2>{total_pontos}</h2><p>Pontos da comunidade</p></div>', unsafe_allow_html=True)
    with b:
        st.markdown(f'<div class="metric-card"><div class="metric-icon">🎟️</div><h2>{total_cotas}</h2><p>Cotas em rifas</p></div>', unsafe_allow_html=True)
    with c:
        st.markdown(f'<div class="metric-card"><div class="metric-icon">🏆</div><h2>{total_vitorias}</h2><p>Vitórias registradas</p></div>', unsafe_allow_html=True)

    st.subheader("🏁 Top 10 jogadores GarageHub")
    for pos, item in enumerate(ranking[:10], start=1):
        render_card_gamificacao(item, pos=pos)


def render_gamificacao_cliente(usuario):
    st.markdown('''
    <div class="pro-hero">
        <h2>🎮 Minha Gamificação</h2>
        <p>Seu nível, pontos, conquistas, cotas de rifas e posição no ranking da comunidade.</p>
    </div>
    ''', unsafe_allow_html=True)

    try:
        todos_usuarios_rank = listar_usuarios()
        todos_minis_rank = buscar_todas_minis()
        rifas_rank = buscar_rifas()
        rifa_numeros_rank = buscar_todos_numeros_rifas()
    except Exception as e:
        st.error(f"Não foi possível montar a gamificação agora: {e}")
        return

    clientes = [u for u in todos_usuarios_rank if u.get("tipo") != "admin"]
    ranking = calcular_gamificacao_clientes(clientes, todos_minis_rank, rifas_rank, rifa_numeros_rank)
    uid_logado = str(usuario.get("id"))
    meu_item = None
    minha_pos = None
    for pos, item in enumerate(ranking, start=1):
        if str((item.get("cliente") or {}).get("id")) == uid_logado:
            meu_item = item
            minha_pos = pos
            break

    if meu_item:
        render_card_gamificacao(meu_item, pos=minha_pos, destaque_voce=True)
    else:
        st.info("Você ainda não entrou no ranking. Participe de compras, rifas ou tenha minis lançadas na garagem.")

    st.subheader("👑 Top 5 da comunidade")
    for pos, item in enumerate(ranking[:5], start=1):
        render_card_gamificacao(item, pos=pos, destaque_voce=str((item.get("cliente") or {}).get("id")) == uid_logado)


def render_admin_executivo(clientes, minis, pedidos):
    faturamento = sum(float(m.get("valor_pago") or 0) for m in minis if (m.get("status_pagamento") or "") == "pago")
    estoque_estimado = sum(float(m.get("valor_estimado") or 0) for m in minis)
    pendentes = len([p for p in pedidos if (p.get("status") or "") in ["solicitado", "pendente", "reservado", "aguardando_pix"]])
    concluidos = len([p for p in pedidos if (p.get("status") or "") == "concluido"])
    st.markdown(f'''
    <div class="pro-hero"><h2>📊 Dashboard Executivo</h2><p>Visão consolidada para o admin: faturamento, pedidos, estoque estimado e crescimento da comunidade.</p></div>
    <div class="pro-grid">
        <div class="pro-card"><h3>💰 Faturamento</h3><p><strong>{money(faturamento)}</strong><br>Total pago lançado na garagem.</p></div>
        <div class="pro-card"><h3>📦 Pedidos abertos</h3><p><strong>{pendentes}</strong><br>Solicitados, reservados ou aguardando Pix.</p></div>
        <div class="pro-card"><h3>✅ Pedidos concluídos</h3><p><strong>{concluidos}</strong><br>Pedidos finalizados e lançados.</p></div>
        <div class="pro-card"><h3>👥 Clientes</h3><p><strong>{len(clientes)}</strong><br>Base cadastrada na comunidade.</p></div>
        <div class="pro-card"><h3>🏎️ Minis lançadas</h3><p><strong>{len(minis)}</strong><br>Itens oficiais nas garagens.</p></div>
        <div class="pro-card"><h3>💎 Valor estimado</h3><p><strong>{money(estoque_estimado)}</strong><br>Valor estimado total do acervo.</p></div>
    </div>
    ''', unsafe_allow_html=True)


def render_hall_automatico(clientes, minis):
    ranking = calcular_ranking(clientes, minis)
    st.markdown('<div class="pro-hero"><h2>🏆 Hall da Fama Automático</h2><p>Ranking gerado pelo próprio sistema com base em compras, coleção e raridades.</p></div>', unsafe_allow_html=True)
    if not ranking:
        st.info("Ainda não há dados suficientes para montar o Hall da Fama.")
        return
    html_cards = []
    for pos, item in enumerate(ranking[:6], start=1):
        c = item["cliente"]
        medalha = "🥇" if pos == 1 else "🥈" if pos == 2 else "🥉" if pos == 3 else "🏁"
        html_cards.append(f'''<div class="pro-card"><h3>{medalha} #{pos} {html.escape(str(c.get("nome") or "Cliente"))}</h3><p><strong>{money(item["total_pago"])}</strong> em compras pagas<br>{item["qtd"]} mini(s) na garagem • {item["raras"]} rara(s)<br>Valor estimado: <strong>{money(item["valor_estimado"])}</strong></p></div>''')
    st.markdown('<div class="pro-grid">' + ''.join(html_cards) + '</div>', unsafe_allow_html=True)


def render_timeline_pedidos(pedidos, clientes_por_id=None):
    clientes_por_id = clientes_por_id or {}
    st.markdown('<div class="pro-hero"><h2>📦 Timeline Premium de Pedidos</h2><p>Acompanhamento visual do ciclo comercial: pedido, reserva, Pix, conclusão e entrega na garagem.</p></div>', unsafe_allow_html=True)
    if not pedidos:
        st.info("Ainda não há pedidos para exibir na timeline.")
        return
    for p in pedidos[:20]:
        cliente = clientes_por_id.get(p.get("usuario_id"), {})
        st.markdown(f'''<div class="timeline-item"><strong>Pedido #{p.get("id")} • {status_label(p.get("status"))}</strong><br>{html.escape(str(p.get("nome") or "Mini"))} — {money(p.get("valor") or 0)}<br>Cliente: {html.escape(str(cliente.get("nome") or "Você"))} • {html.escape(str(p.get("criado_em") or ""))[:19]}</div>''', unsafe_allow_html=True)


def render_notificacoes_demo(usuario, pedidos=None):
    pedidos = pedidos or []
    abertos = len([p for p in pedidos if (p.get("status") or "") in ["solicitado", "pendente", "reservado", "aguardando_pix"]])
    concluidos = len([p for p in pedidos if (p.get("status") or "") == "concluido"])
    nome = html.escape(str(usuario.get("nome") or "colecionador"))
    st.markdown(f'''<div class="pro-hero"><h2>🔔 Central de Notificações</h2><p>Alertas internos preparados para evoluir para e-mail, WhatsApp ou push notification.</p></div><div class="notify-item"><strong>Olá, {nome}</strong><br>Você tem {abertos} pedido(s) em andamento.</div><div class="notify-item"><strong>Garagem atualizada</strong><br>{concluidos} pedido(s) já foram concluídos e lançados.</div><div class="notify-item"><strong>VIP e Marketplace</strong><br>Novidades, promoções e drops exclusivos poderão aparecer aqui.</div>''', unsafe_allow_html=True)


def render_mobile_preview(usuario):
    perfil = "VIP" if (usuario.get("nivel_cliente") or "comum") == "vip" else "Cliente"
    st.markdown(f'''<div class="pro-hero"><h2>📱 Visual Mobile / App Mode</h2><p>Prévia visual de como o GarageHub pode ficar em versão mobile-first.</p></div><div class="mobile-preview"><div class="mobile-top"><h3>🏁 GarageHub</h3><p>{html.escape(str(usuario.get("nome") or "Colecionador"))} • {perfil}</p></div><div class="mobile-body"><div class="pro-card"><h3>🏎️ Minha garagem</h3><p>Cards rápidos, pedidos, Pix e ranking em formato app.</p></div><div class="checkout-box"><h3>💳 Checkout</h3><p>Pix, comprovante e status visual.</p></div></div><div class="mobile-nav"><span>🏠<br>Home</span><span>🛒<br>Loja</span><span>📦<br>Pedidos</span><span>👤<br>Perfil</span></div></div>''', unsafe_allow_html=True)


def render_perfil_publico(usuario, minis):
    favoritas = [m for m in minis if (m.get("raridade") or "") in ["STH", "RLC", "Chase", "Especial"]]
    destaque = favoritas[0] if favoritas else (minis[0] if minis else {})
    st.markdown(f'''<div class="profile-banner"><h2>👤 Perfil público do colecionador</h2><p><strong>{html.escape(str(usuario.get("nome") or "Colecionador"))}</strong> • {"Membro VIP" if (usuario.get("nivel_cliente") or "comum") == "vip" else "Cliente comum"}</p><p>Garagem: <strong>{len(minis)}</strong> mini(s) • Destaque: <strong>{html.escape(str(destaque.get("nome") or "em breve"))}</strong></p><p>Código: <strong>{html.escape(str(usuario.get("codigo_membro") or "-"))}</strong></p></div>''', unsafe_allow_html=True)


def render_checkout_real_visual(pedidos):
    st.markdown('<div class="pro-hero"><h2>💳 Checkout Pix Real — Estrutura Visual</h2><p>Área pronta para evoluir de Pix assistido para integração real com provedor de pagamento.</p></div>', unsafe_allow_html=True)
    if not pedidos:
        st.info("Nenhum pedido disponível para checkout ainda.")
        return
    for p in pedidos[:5]:
        st.markdown(pix_card_html(p, f"Checkout do pedido #{p.get('id')}"), unsafe_allow_html=True)
        st.caption("Próximo passo técnico: conectar Mercado Pago/Pix API e webhook de confirmação automática.")


def detectar_mini_por_texto(nome_arquivo="", observacao=""):
    # Heurística local para simular o Scanner IA sem depender de API externa ainda.
    bruto = f"{nome_arquivo} {observacao}".lower()

    marca = "Hot Wheels"
    if "mini gt" in bruto or "minigt" in bruto:
        marca = "Mini GT"
    elif "kaido" in bruto:
        marca = "Mini GT / Kaido House"
    elif "matchbox" in bruto:
        marca = "Matchbox"

    raridade = "Comum"
    if any(t in bruto for t in ["sth", "super treasure", "super treasure hunt"]):
        raridade = "STH"
    elif any(t in bruto for t in ["rlc", "red line"]):
        raridade = "RLC"
    elif any(t in bruto for t in ["chase", "kaido"]):
        raridade = "Chase"
    elif any(t in bruto for t in ["premium", "car culture", "team transport"]):
        raridade = "Premium"
    elif any(t in bruto for t in ["th", "treasure hunt"]):
        raridade = "TH"
    elif any(t in bruto for t in ["especial", "limited", "exclusive"]):
        raridade = "Especial"

    ano = ""
    m = re.search(r"(20\d{2}|19\d{2})", bruto)
    if m:
        ano = m.group(1)

    serie = ""
    if "gulf" in bruto:
        serie = "Gulf"
    elif "fast" in bruto or "furious" in bruto:
        serie = "Fast & Furious"
    elif "boulevard" in bruto:
        serie = "Boulevard"
    elif "car culture" in bruto:
        serie = "Car Culture"
    elif "kaido" in bruto:
        serie = "Kaido House"

    nome = Path(str(nome_arquivo or "")).stem.replace("_", " ").replace("-", " ").strip().title()
    if not nome:
        nome = "Mini identificada pelo scanner"

    base_valor = {
        "Comum": 25.0,
        "TH": 45.0,
        "Premium": 65.0,
        "Especial": 80.0,
        "Chase": 140.0,
        "RLC": 220.0,
        "STH": 250.0,
    }.get(raridade, 25.0)

    confianca = 62
    if serie:
        confianca += 8
    if ano:
        confianca += 7
    if raridade != "Comum":
        confianca += 12
    confianca = min(confianca, 94)

    return {
        "nome": nome,
        "marca": marca,
        "serie": serie,
        "ano": ano,
        "raridade": raridade,
        "valor": base_valor,
        "valor_estimado": base_valor,
        "confianca": confianca,
    }


def render_scanner_ia_demo():
    """Scanner IA Premium integrado ao GarageHub usando Gemini Vision."""
    usuario_atual = st.session_state.get("usuario") or {}
    is_admin = usuario_atual.get("tipo") == "admin"

    st.markdown('''
    <div class="scanner-hero">
        <div class="scanner-kicker">🤖 Scanner IA Premium</div>
        <h2>TRINANES AI GARAGE VISION</h2>
        <p>Use câmera ou upload para analisar mini solto, blister, frente/verso ou expositor. A IA retorna ficha estruturada e você pode salvar direto na garagem.</p>
    </div>
    <div class="pro-grid">
        <div class="scanner-step"><h3>📷 1. Captura</h3><p>Foto da mini, embalagem, blister ou expositor.</p></div>
        <div class="scanner-step"><h3>🧠 2. IA Gemini</h3><p>Modelo, marca, série, raridade, SKU, cores e valor estimado.</p></div>
        <div class="scanner-step"><h3>🏁 3. Salvar</h3><p>Valide/ajuste os dados e salve na garagem ou publique na loja.</p></div>
    </div>
    ''', unsafe_allow_html=True)

    try:
        import json
        import io
        from PIL import Image
        from google import genai
        from google.genai import types
    except Exception as e:
        st.error("Dependências do Scanner IA não instaladas.")
        st.info("No requirements.txt, inclua: google-genai e Pillow")
        st.code(str(e))
        return

    try:
        gemini_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        st.error("GEMINI_API_KEY não encontrada nos Secrets do Streamlit.")
        st.info('Adicione nos Secrets: GEMINI_API_KEY="sua_chave"')
        return

    def preparar_imagem_para_gemini(arquivo):
        if arquivo is None:
            return None
        try:
            imagem = Image.open(arquivo)
            if imagem.mode != "RGB":
                imagem = imagem.convert("RGB")
            imagem.thumbnail((1024, 1024))
            buffer = io.BytesIO()
            imagem.save(buffer, format="JPEG", quality=85, optimize=True)
            buffer.seek(0)
            return types.Part.from_bytes(data=buffer.getvalue(), mime_type="image/jpeg")
        except Exception as e:
            st.error(f"Erro ao preparar imagem: {e}")
            return None

    def limpar_json_scanner(texto):
        texto = str(texto or "").strip().replace("```json", "").replace("```", "").strip()
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if match:
            texto = match.group(0)
        return json.loads(texto)

    def prompt_scanner(modo):
        return f'''
Você é especialista profissional em miniaturas diecast 1:64:
Hot Wheels, Mini GT, Kaido House, Matchbox, M2 Machines, GreenLight, Tarmac Works, Inno64, Johnny Lightning e similares.

Tipo de análise solicitado pelo usuário:
{modo}

As imagens podem conter mini solto, blister completo, frente/verso do blister, expositor, vários minis juntos ou coleção inteira.

Sua missão: identificar o máximo possível SEM inventar dados.
Retorne APENAS JSON válido, sem texto antes e sem texto depois.

{{
  "tipo_imagem_detectada": "",
  "modelo_detectado": "",
  "fabricante_detectado": "",
  "marca_linha": "",
  "possivel_serie": "",
  "series_index": "",
  "sku": "",
  "ano_lancamento": "",
  "possivel_raridade": "",
  "escala": "",
  "casting": "",
  "cor_principal": "",
  "cor_base": "",
  "cor_vidro": "",
  "cor_interior": "",
  "tipo_roda": "",
  "pais_origem": "",
  "designer": "",
  "valor_estimado_brasil": "",
  "nivel_confianca": "",
  "detalhes_visuais": "",
  "alerta_colecao": "",
  "observacoes": "",
  "itens_detectados": []
}}

Regras obrigatórias:
- Nunca invente SKU, ano, designer ou série.
- Se não tiver certeza, use "Não identificado".
- Para raridade, use apenas: "Comum", "TH", "STH", "Premium", "RLC", "Chase", "Especial", "Limitado", "Não identificado".
- O valor estimado deve ser em reais, aproximado, e com faixa. Exemplo: "R$ 80 a R$ 150".
- Se for mini solto, priorize modelo, fabricante provável, cor, rodas, decals e confiança.
- Se for blister, tente ler SKU, série, ano e informações impressas.
- Se for expositor/coleção, preencha itens_detectados com uma lista simples dos minis encontrados.
- nivel_confianca deve ser percentual, exemplo: "72%".
- alerta_colecao deve dizer se parece item comum, raro, premium, chase ou item que merece pesquisa manual.
'''

    def primeiro_numero_reais(valor):
        texto = str(valor or "")
        nums = re.findall(r"\d+[\.,]?\d*", texto)
        if not nums:
            return 0.0
        try:
            return float(nums[0].replace(".", "").replace(",", "."))
        except Exception:
            return 0.0

    def valor_limpo(dados, chave, padrao="Não identificado"):
        valor = dados.get(chave, padrao) if isinstance(dados, dict) else padrao
        if valor is None or str(valor).strip() == "":
            return padrao
        return str(valor).strip()

    modo_analise = st.selectbox(
        "Tipo de análise",
        ["🚗 Mini solto", "📦 Blister frente e verso", "🖼️ Expositor / coleção", "🔍 Modo automático"],
        key="scanner_ai_modo_analise"
    )

    envio = st.radio(
        "Como quer enviar a imagem?",
        ["📷 Usar câmera", "🖼️ Enviar foto"],
        horizontal=True,
        key="scanner_ai_tipo_envio"
    )

    foto_1 = foto_2 = foto_3 = None
    if envio == "📷 Usar câmera":
        foto_1 = st.camera_input("Foto principal", key="scanner_ai_camera_1")
        if modo_analise == "📦 Blister frente e verso":
            foto_2 = st.camera_input("Foto do verso do blister", key="scanner_ai_camera_2")
        elif modo_analise in ["🖼️ Expositor / coleção", "🔍 Modo automático"]:
            foto_2 = st.camera_input("Foto extra opcional", key="scanner_ai_camera_2_extra")
    else:
        foto_1 = st.file_uploader("Foto principal", type=["jpg", "jpeg", "png", "webp"], key="scanner_ai_upload_1")
        if modo_analise == "📦 Blister frente e verso":
            foto_2 = st.file_uploader("Foto do verso do blister", type=["jpg", "jpeg", "png", "webp"], key="scanner_ai_upload_2")
        elif modo_analise in ["🖼️ Expositor / coleção", "🔍 Modo automático"]:
            foto_2 = st.file_uploader("Foto extra opcional", type=["jpg", "jpeg", "png", "webp"], key="scanner_ai_upload_2_extra")
            foto_3 = st.file_uploader("Mais uma foto opcional", type=["jpg", "jpeg", "png", "webp"], key="scanner_ai_upload_3")

    fotos_validas = [f for f in [foto_1, foto_2, foto_3] if f is not None]
    if fotos_validas:
        st.image(fotos_validas[0], caption="Prévia da foto principal", use_container_width=True)

    if st.button("🔥 Analisar mini com IA", use_container_width=True, key="scanner_ai_analisar"):
        if not fotos_validas:
            st.error("Envie pelo menos uma foto.")
            return

        with st.spinner("Analisando com Gemini IA..."):
            imagens = []
            for foto in fotos_validas:
                parte = preparar_imagem_para_gemini(foto)
                if parte:
                    imagens.append(parte)

            if not imagens:
                st.error("Nenhuma imagem válida foi encontrada. Tente outra foto.")
                return

            try:
                client = genai.Client(api_key=gemini_key)
                resposta = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[prompt_scanner(modo_analise)] + imagens,
                    config={"temperature": 0.2, "response_mime_type": "application/json"}
                )
                dados = limpar_json_scanner(resposta.text)
                st.session_state["scanner_ai_resultado"] = dados
                st.session_state["scanner_ai_tem_foto"] = True
                st.success("Mini analisado com sucesso!")
            except Exception as e:
                st.error("Erro ao consultar a IA.")
                st.info("Possíveis causas: limite da API, chave inválida, billing desativado ou imagem muito pesada.")
                st.code(str(e))
                return

    dados = st.session_state.get("scanner_ai_resultado")
    if not dados:
        st.info("Envie uma foto e clique em Analisar mini com IA para gerar a ficha.")
        return

    nome_sugerido = valor_limpo(dados, "modelo_detectado", "Mini identificada pela IA")
    marca_sugerida = valor_limpo(dados, "fabricante_detectado", "Hot Wheels")
    linha_sugerida = valor_limpo(dados, "marca_linha", "")
    serie_sugerida = valor_limpo(dados, "possivel_serie", linha_sugerida if linha_sugerida != "Não identificado" else "")
    ano_sugerido = valor_limpo(dados, "ano_lancamento", "")
    raridade_sugerida = valor_limpo(dados, "possivel_raridade", "Não identificado")
    valor_estimado_txt = valor_limpo(dados, "valor_estimado_brasil", "R$ 0")
    valor_estimado_num = primeiro_numero_reais(valor_estimado_txt)
    confianca = valor_limpo(dados, "nivel_confianca", "0%")

    st.markdown(f'''
    <div class="scanner-result">
        <div class="scanner-score">{html.escape(confianca)}</div>
        <h3>Resultado da IA</h3>
        <p><b>{html.escape(nome_sugerido)}</b> • {html.escape(marca_sugerida)} • {html.escape(raridade_sugerida)}</p>
        <p>Série: <b>{html.escape(serie_sugerida or 'Não identificado')}</b> • Ano: <b>{html.escape(ano_sugerido or 'Não identificado')}</b> • Valor IA: <b>{html.escape(valor_estimado_txt)}</b></p>
        <p>{html.escape(valor_limpo(dados, 'alerta_colecao', ''))}</p>
    </div>
    ''', unsafe_allow_html=True)

    campos_principais = [
        "tipo_imagem_detectada", "modelo_detectado", "fabricante_detectado", "marca_linha",
        "possivel_serie", "series_index", "sku", "ano_lancamento", "possivel_raridade",
        "escala", "casting", "cor_principal", "tipo_roda", "pais_origem", "designer",
        "valor_estimado_brasil", "nivel_confianca", "detalhes_visuais", "alerta_colecao", "observacoes"
    ]
    with st.expander("📋 Ver ficha completa da IA", expanded=False):
        for campo in campos_principais:
            st.write(f"**{campo.replace('_', ' ').title()}:** {dados.get(campo, 'Não identificado')}")
        itens = dados.get("itens_detectados", [])
        if itens:
            st.write("**Itens detectados:**")
            for item in itens:
                st.write(item)

    with st.expander("✏️ Validar e ajustar antes de salvar", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            s_nome = st.text_input("Nome identificado", value=nome_sugerido, key="scanner_ai_nome_final")
            s_marca = st.text_input("Marca", value=marca_sugerida, key="scanner_ai_marca_final")
            s_serie = st.text_input("Série / Linha", value=serie_sugerida, key="scanner_ai_serie_final")
            s_ano = st.text_input("Ano", value=ano_sugerido if ano_sugerido != "Não identificado" else "", key="scanner_ai_ano_final")
        with c2:
            opcoes_r = ["Comum", "TH", "STH", "Premium", "RLC", "Chase", "Especial", "Limitado", "Não identificado"]
            idx_r = opcoes_r.index(raridade_sugerida) if raridade_sugerida in opcoes_r else len(opcoes_r) - 1
            s_raridade = st.selectbox("Raridade", opcoes_r, index=idx_r, key="scanner_ai_raridade_final")
            s_valor_pago = st.number_input("Valor pago / venda", min_value=0.0, step=1.0, value=0.0, key="scanner_ai_valor_pago_final")
            s_estimado = st.number_input("Valor estimado", min_value=0.0, step=1.0, value=float(valor_estimado_num or 0), key="scanner_ai_estimado_final")
            s_destaque = st.text_input("Destaque / observação", value="Scanner IA Premium", key="scanner_ai_destaque_final")

    json_data = json.dumps(dados, ensure_ascii=False, indent=2)
    st.download_button("⬇️ Baixar JSON do scanner", data=json_data, file_name="mini_scanner_resultado.json", mime="application/json", use_container_width=True, key="scanner_ai_download_json")

    foto_para_salvar = foto_1 or (fotos_validas[0] if fotos_validas else None)

    if not is_admin:
        if st.button("➕ Adicionar à minha garagem", use_container_width=True, key="scanner_ai_add_minha_garagem"):
            if not usuario_atual.get("id"):
                st.error("Usuário não identificado. Faça login novamente.")
                return
            foto_url = upload_storage_loja(foto_para_salvar, s_nome) if foto_para_salvar is not None else ""
            cadastrar_mini(
                usuario_atual.get("id"), s_nome, s_marca, s_serie, s_ano, s_raridade,
                float(s_valor_pago or 0), float(s_estimado or 0), foto_url, "pago", "scanner", s_destaque
            )
            try:
                supabase.table("scanner_logs").insert({
                    "usuario_id": usuario_atual.get("id"),
                    "imagem_url": foto_url,
                    "resultado": s_nome,
                    "confianca": confianca,
                }).execute()
            except Exception:
                pass
            st.success("Mini adicionada à sua garagem pelo Scanner IA Premium.")
            st.rerun()
        return

    st.markdown('<div class="checkout-box"><h3>👑 Ações de admin</h3><p>Use o resultado validado para publicar na loja ou lançar diretamente na garagem de um cliente.</p></div>', unsafe_allow_html=True)
    ac1, ac2 = st.columns(2)
    with ac1:
        categoria_scanner = st.selectbox("Categoria da Loja", CATEGORIAS_LOJA, key="scanner_ai_categoria_loja")
        qtd_loja = st.number_input("Quantidade para publicar na loja", min_value=1, step=1, value=1, key="scanner_ai_qtd_loja")
        if st.button("🛒 Publicar na loja", key="scanner_ai_publicar_loja", use_container_width=True):
            foto_url = upload_storage_loja(foto_para_salvar, s_nome) if foto_para_salvar is not None else ""
            destaque_loja = atualizar_destaque_com_qtd_e_categoria(s_destaque, int(qtd_loja or 1), categoria_scanner)
            try:
                cadastrar_loja_mini(s_nome, s_marca, s_serie, s_ano, s_raridade, float(s_valor_pago or s_estimado or 0), float(s_estimado or 0), foto_url, "disponivel", destaque_loja)
                st.success("Mini publicada na loja pelo Scanner IA Premium.")
                st.rerun()
            except Exception as e:
                st.error(f"Não consegui publicar na loja: {e}")
    with ac2:
        try:
            clientes_scanner = [u for u in listar_usuarios() if str(u.get("tipo") or "usuario").lower() != "admin"]
        except Exception:
            clientes_scanner = []
        if clientes_scanner:
            mapa_clientes = {f"{c.get('nome','')} — {c.get('email','')}": c for c in clientes_scanner}
            cliente_label = st.selectbox("Cliente para lançar na garagem", list(mapa_clientes.keys()), key="scanner_ai_cliente_garagem")
            status_lancar = st.selectbox("Status pagamento", ["pago", "pendente", "reservado", "pre_datado"], key="scanner_ai_status_lancar")
            data_pagamento_scanner = None
            if status_lancar in ["pendente", "reservado", "pre_datado"]:
                data_pagamento_scanner = st.date_input("Data prevista de pagamento (opcional)", value=None, format="DD/MM/YYYY", key="scanner_ai_data_pagamento_lancar")
            if st.button("🏎️ Lançar na garagem do cliente", key="scanner_ai_lancar_garagem", use_container_width=True):
                foto_url = upload_storage_loja(foto_para_salvar, s_nome) if foto_para_salvar is not None else ""
                cliente_sel = mapa_clientes[cliente_label]
                cadastrar_mini(cliente_sel["id"], s_nome, s_marca, s_serie, s_ano, s_raridade, float(s_valor_pago or 0), float(s_estimado or 0), foto_url, status_lancar, "scanner/admin", s_destaque, data_pagamento_scanner)
                try:
                    supabase.table("scanner_logs").insert({
                        "usuario_id": cliente_sel.get("id"),
                        "imagem_url": foto_url,
                        "resultado": s_nome,
                        "confianca": confianca,
                    }).execute()
                except Exception:
                    pass
                st.success("Mini lançada na garagem do cliente pelo Scanner IA Premium.")
                st.rerun()
        else:
            st.info("Cadastre clientes para lançar direto na garagem.")




# =========================
# RIFAS GARAGEHUB V6 — GRADE VISUAL
# =========================
def sql_rifas_necessario():
    return """
-- GarageHub Rifas V6
create table if not exists rifas (
    id uuid primary key default gen_random_uuid(),
    titulo text,
    premio_nome text,
    premio_foto_url text,
    descricao text,
    valor_numero numeric default 0,
    qtd_numeros integer default 100,
    modo_premiacao text default 'sorteio_normal',
    status text default 'aberta',
    numero_sorteado integer,
    vencedor_usuario_id text,
    top_comprador_usuario_id text,
    top_ganhador_usuario_id text,
    resultado_texto text,
    criado_em timestamptz default now()
);

create table if not exists rifa_numeros (
    id uuid primary key default gen_random_uuid(),
    rifa_id text not null,
    usuario_id text not null,
    numero integer not null,
    status_pagamento text default 'pendente',
    criado_em timestamptz default now()
);

create unique index if not exists idx_rifa_numero_unico
on rifa_numeros (rifa_id, numero);
    """.strip()


def modo_rifa_label(modo):
    mapa = {
        "sorteio_normal": "🎲 Sorteio normal",
        "top_comprador": "💰 Top comprador",
        "top_ganhador": "👑 Top ganhador",
        "hibrida": "🔥 Híbrida",
        "sorteio_top_comprador": "🔥 Híbrida",
        "sorteio_top_ganhador": "🔥 Híbrida",
        "somente_top_comprador": "💰 Top comprador",
        "somente_top_ganhador": "👑 Top ganhador",
    }
    return mapa.get(str(modo or "sorteio_normal"), str(modo or "Rifa"))


def rifa_modo_descricao(modo):
    modo = str(modo or "sorteio_normal")
    mapa = {
        "sorteio_normal": "Sorteia automaticamente 1 número entre os números pagos/reservados.",
        "top_comprador": "Não sorteia número. Premia quem comprou mais números nesta rifa.",
        "top_ganhador": "Não sorteia número. Premia quem mais venceu no histórico de rifas.",
        "hibrida": "Faz os 3 resultados: sorteio normal + Top comprador + Top ganhador histórico.",
        "sorteio_top_comprador": "Compatibilidade: tratado como rifa híbrida.",
        "sorteio_top_ganhador": "Compatibilidade: tratado como rifa híbrida.",
        "somente_top_comprador": "Compatibilidade: tratado como Top comprador.",
        "somente_top_ganhador": "Compatibilidade: tratado como Top ganhador.",
    }
    return mapa.get(modo, "Modo de premiação da rifa.")


def buscar_rifas():
    return supabase.table("rifas").select("*").order("criado_em", desc=True).execute().data


def criar_rifa(titulo, premio_nome, premio_foto_url, descricao, valor_numero, qtd_numeros, modo_premiacao, status="aberta"):
    supabase.table("rifas").insert({
        "titulo": titulo,
        "premio_nome": premio_nome,
        "premio_foto_url": premio_foto_url or "",
        "descricao": descricao or "",
        "valor_numero": float(valor_numero or 0),
        "qtd_numeros": int(qtd_numeros or 100),
        "modo_premiacao": modo_premiacao or "sorteio_normal",
        "status": status or "aberta",
    }).execute()


def atualizar_rifa(rifa_id, dados):
    supabase.table("rifas").update(dados).eq("id", rifa_id).execute()


def excluir_rifa(rifa_id):
    try:
        supabase.table("rifa_numeros").delete().eq("rifa_id", str(rifa_id)).execute()
    except Exception:
        pass
    supabase.table("rifas").delete().eq("id", rifa_id).execute()


def buscar_numeros_rifa(rifa_id):
    return supabase.table("rifa_numeros").select("*").eq("rifa_id", str(rifa_id)).order("numero").execute().data


def atualizar_numero_rifa(numero_id, dados):
    """Atualiza um número específico da rifa."""
    supabase.table("rifa_numeros").update(dados).eq("id", numero_id).execute()


def atualizar_numeros_rifa_lote(rifa_id, usuario_id, status_origem, novo_status):
    """Atualiza em lote os números de um cliente em uma rifa por status."""
    query = (
        supabase.table("rifa_numeros")
        .update({"status_pagamento": novo_status})
        .eq("rifa_id", str(rifa_id))
        .eq("usuario_id", str(usuario_id))
    )

    if status_origem and status_origem != "todos":
        query = query.eq("status_pagamento", status_origem)

    query.execute()


def excluir_numeros_rifa_lote(rifa_id, usuario_id, status_origem):
    """Remove em lote números de um cliente em uma rifa por status."""
    query = (
        supabase.table("rifa_numeros")
        .delete()
        .eq("rifa_id", str(rifa_id))
        .eq("usuario_id", str(usuario_id))
    )

    if status_origem and status_origem != "todos":
        query = query.eq("status_pagamento", status_origem)

    query.execute()


def agrupar_numeros_rifa_por_cliente_status(numeros):
    """Agrupa números por cliente e status para facilitar confirmação/cancelamento em lote."""
    grupos = {}

    for item in numeros or []:
        uid = str(item.get("usuario_id") or "")
        status = str(item.get("status_pagamento") or "pendente").lower()
        chave = (uid, status)

        if chave not in grupos:
            grupos[chave] = {
                "usuario_id": uid,
                "status": status,
                "numeros": [],
                "ids": [],
            }

        try:
            grupos[chave]["numeros"].append(int(item.get("numero")))
        except Exception:
            pass

        if item.get("id"):
            grupos[chave]["ids"].append(item.get("id"))

    return sorted(
        grupos.values(),
        key=lambda g: (str(g.get("status")), str(g.get("usuario_id")))
    )


def buscar_numeros_rifa_fresco(rifa_id):
    """Busca números sempre direto do Supabase para a tela do cliente refletir o admin."""
    try:
        return (
            supabase.table("rifa_numeros")
            .select("id,rifa_id,usuario_id,numero,status_pagamento,criado_em")
            .eq("rifa_id", str(rifa_id))
            .order("numero")
            .execute()
            .data
        )
    except Exception:
        return buscar_numeros_rifa(rifa_id)


def parse_numeros_especificos(texto):
    """Converte texto como '7, 13, 22-25' em lista de números únicos e ordenados."""
    texto = str(texto or "").strip()
    if not texto:
        return []

    numeros = []
    partes = re.split(r"[,;\s]+", texto)

    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue

        if "-" in parte:
            try:
                ini, fim = parte.split("-", 1)
                ini = int(ini.strip())
                fim = int(fim.strip())
                if ini > fim:
                    ini, fim = fim, ini
                numeros.extend(range(ini, fim + 1))
            except Exception:
                continue
        else:
            try:
                numeros.append(int(parte))
            except Exception:
                continue

    vistos = set()
    limpos = []
    for n in numeros:
        if n not in vistos:
            vistos.add(n)
            limpos.append(n)

    return sorted(limpos)


def registrar_numeros_rifa(rifa, usuario_id, qtd, status_pagamento="pago", numeros_especificos=None):
    rifa_id = str(rifa.get("id"))
    qtd_total = int(rifa.get("qtd_numeros") or 100)
    numeros_especificos = numeros_especificos or []

    numeros_atuais = buscar_numeros_rifa(rifa_id)
    ocupados = set()
    for n in numeros_atuais:
        try:
            ocupados.add(int(n.get("numero")))
        except Exception:
            pass

    if numeros_especificos:
        escolhidos = []
        fora_do_limite = []
        ja_ocupados = []

        for numero in numeros_especificos:
            try:
                numero = int(numero)
            except Exception:
                continue

            if numero < 1 or numero > qtd_total:
                fora_do_limite.append(numero)
            elif numero in ocupados:
                ja_ocupados.append(numero)
            else:
                escolhidos.append(numero)

        if fora_do_limite:
            return False, f"Número(s) fora do limite 1 a {qtd_total}: {', '.join(map(str, fora_do_limite))}."

        if ja_ocupados:
            return False, f"Número(s) já escolhido(s): {', '.join(map(str, ja_ocupados))}."

        if not escolhidos:
            return False, "Informe ao menos um número válido para lançar."

    else:
        qtd = int(qtd or 0)
        if qtd <= 0:
            return False, "Informe uma quantidade maior que zero."

        disponiveis = [n for n in range(1, qtd_total + 1) if n not in ocupados]

        if qtd > len(disponiveis):
            return False, f"Só existem {len(disponiveis)} número(s) disponível(is) nesta rifa."

        escolhidos = disponiveis[:qtd]

    novos = []
    for numero in escolhidos:
        novos.append({
            "rifa_id": rifa_id,
            "usuario_id": str(usuario_id),
            "numero": int(numero),
            "status_pagamento": status_pagamento or "pago",
        })

    supabase.table("rifa_numeros").insert(novos).execute()

    lista = ", ".join(map(str, escolhidos[:30]))
    extra = "" if len(escolhidos) <= 30 else f" ... +{len(escolhidos) - 30}"
    return True, f"{len(escolhidos)} número(s) lançado(s): {lista}{extra}."


def nome_cliente_por_id(clientes_por_id, usuario_id):
    c = clientes_por_id.get(str(usuario_id)) or clientes_por_id.get(usuario_id) or {}
    return c.get("nome") or "Cliente"


def calcular_top_comprador_rifa(numeros):
    ranking = {}
    for n in numeros or []:
        uid = str(n.get("usuario_id") or "")
        if not uid:
            continue
        status = str(n.get("status_pagamento") or "pendente").lower()
        if status in ["pago", "pendente", "reservado", "aguardando_pix"]:
            ranking.setdefault(uid, 0)
            ranking[uid] += 1

    if not ranking:
        return None, 0

    uid_top = sorted(ranking.items(), key=lambda x: x[1], reverse=True)[0][0]
    return uid_top, ranking[uid_top]


def calcular_top_ganhador_geral(rifas, vencedores_atuais=None):
    ranking = {}
    campos = ["vencedor_usuario_id", "top_comprador_usuario_id", "top_ganhador_usuario_id"]

    for r in rifas or []:
        if str(r.get("status") or "").lower() != "sorteada":
            continue
        for campo in campos:
            uid = str(r.get(campo) or "")
            if uid and uid.lower() not in ["none", "null", ""]:
                ranking.setdefault(uid, 0)
                ranking[uid] += 1

    for uid in vencedores_atuais or []:
        uid = str(uid or "")
        if uid and uid.lower() not in ["none", "null", ""]:
            ranking.setdefault(uid, 0)
            ranking[uid] += 1

    if not ranking:
        return None, 0

    uid_top = sorted(ranking.items(), key=lambda x: x[1], reverse=True)[0][0]
    return uid_top, ranking[uid_top]


def processar_resultado_rifa(rifa, numeros, clientes, rifas_historico):
    modo = rifa.get("modo_premiacao") or "sorteio_normal"
    numeros_validos = [n for n in (numeros or []) if str(n.get("status_pagamento") or "").lower() in ["pago", "reservado"]]
    clientes_por_id = {str(c.get("id")): c for c in clientes}

    vencedor_uid = None
    numero_sorteado = None
    top_comprador_uid = None
    top_ganhador_uid = None
    partes = []

    modos_com_sorteio = ["sorteio_normal", "hibrida", "sorteio_top_comprador", "sorteio_top_ganhador"]
    modos_com_top_comprador = ["top_comprador", "hibrida", "somente_top_comprador", "sorteio_top_comprador"]
    modos_com_top_ganhador = ["top_ganhador", "hibrida", "somente_top_ganhador", "sorteio_top_ganhador"]

    if modo in modos_com_sorteio:
        if not numeros_validos:
            return False, "Não há números pagos/reservados para sortear."
        escolhido = random.choice(numeros_validos)
        vencedor_uid = str(escolhido.get("usuario_id"))
        numero_sorteado = int(escolhido.get("numero") or 0)
        partes.append(f"🎲 Sorteio normal: número {numero_sorteado} — vencedor: {nome_cliente_por_id(clientes_por_id, vencedor_uid)}")

    if modo in modos_com_top_comprador:
        top_comprador_uid, qtd_top = calcular_top_comprador_rifa(numeros)
        if not top_comprador_uid:
            return False, "Não há compradores suficientes para calcular Top comprador."
        partes.append(f"💰 Top comprador: {nome_cliente_por_id(clientes_por_id, top_comprador_uid)} com {qtd_top} número(s)")

    if modo in modos_com_top_ganhador:
        vencedores_atuais = []
        if modo == "hibrida":
            vencedores_atuais = [vencedor_uid, top_comprador_uid]

        top_ganhador_uid, qtd_vitorias = calcular_top_ganhador_geral(rifas_historico, vencedores_atuais)

        if not top_ganhador_uid:
            return False, "Ainda não existe histórico de ganhadores para calcular Top ganhador. Faça primeiro uma rifa normal ou híbrida."

        partes.append(f"👑 Top ganhador: {nome_cliente_por_id(clientes_por_id, top_ganhador_uid)} com {qtd_vitorias} vitória(s) no histórico")

    resultado = " | ".join(partes) if partes else "Rifa processada."

    dados_update = {
        "status": "sorteada",
        "numero_sorteado": numero_sorteado,
        "vencedor_usuario_id": vencedor_uid,
        "top_comprador_usuario_id": top_comprador_uid,
        "top_ganhador_usuario_id": top_ganhador_uid,
        "resultado_texto": resultado,
    }

    try:
        atualizar_rifa(rifa.get("id"), dados_update)
    except Exception:
        atualizar_rifa(rifa.get("id"), {"status": "sorteada"})

    return True, resultado


def resultado_rifa_html(rifa, clientes_por_id):
    if not rifa.get("resultado_texto"):
        return ""

    vencedor = nome_cliente_por_id(clientes_por_id, rifa.get("vencedor_usuario_id")) if rifa.get("vencedor_usuario_id") else "-"
    top_comprador = nome_cliente_por_id(clientes_por_id, rifa.get("top_comprador_usuario_id")) if rifa.get("top_comprador_usuario_id") else "-"
    top_ganhador = nome_cliente_por_id(clientes_por_id, rifa.get("top_ganhador_usuario_id")) if rifa.get("top_ganhador_usuario_id") else "-"
    numero = rifa.get("numero_sorteado") or "-"

    return f"""
    <div class="pro-card hall-glow">
        <h3>🏁 Resultado oficial da rifa</h3>
        <p><strong>{html.escape(str(rifa.get("resultado_texto") or ""))}</strong></p>
        <div class="pro-grid">
            <div class="pro-card"><h3>🎲 Sorteio</h3><p>Número: <strong>{html.escape(str(numero))}</strong><br>Vencedor: <strong>{html.escape(str(vencedor))}</strong></p></div>
            <div class="pro-card"><h3>💰 Top comprador</h3><p><strong>{html.escape(str(top_comprador))}</strong></p></div>
            <div class="pro-card"><h3>👑 Top ganhador</h3><p><strong>{html.escape(str(top_ganhador))}</strong></p></div>
        </div>
    </div>
    """


def render_grade_numeros_rifa(rifa, numeros, clientes_por_id):
    """Renderiza a grade visual dos números da rifa."""
    try:
        qtd_total = int(rifa.get("qtd_numeros") or 0)
    except Exception:
        qtd_total = 0

    if qtd_total <= 0:
        return

    mapa_numeros = {}
    for item in numeros or []:
        try:
            mapa_numeros[int(item.get("numero"))] = item
        except Exception:
            pass

    try:
        numero_vencedor = int(rifa.get("numero_sorteado")) if rifa.get("numero_sorteado") is not None else None
    except Exception:
        numero_vencedor = None

    largura = max(2, len(str(qtd_total)))
    blocos = []

    for numero in range(1, qtd_total + 1):
        item = mapa_numeros.get(numero)
        label = str(numero).zfill(largura)

        if numero_vencedor is not None and numero == numero_vencedor:
            classe = "rifa-num-vencedor"
            tooltip = f"Número {label} — vencedor"
        elif item:
            status = str(item.get("status_pagamento") or "pendente").lower()
            if status == "pago":
                classe = "rifa-num-pago"
            elif status in ["pendente", "reservado", "aguardando_pix"]:
                classe = "rifa-num-pendente"
            else:
                classe = "rifa-num-pendente"

            cliente_nome = nome_cliente_por_id(clientes_por_id, item.get("usuario_id"))
            tooltip = f"Número {label} — {status} — {cliente_nome}"
        else:
            classe = "rifa-num-disponivel"
            tooltip = f"Número {label} — disponível"

        blocos.append(
            f'<div class="rifa-num {classe}" title="{html.escape(tooltip, quote=True)}">{html.escape(label)}</div>'
        )

    ocupados = len(mapa_numeros)
    disponiveis = max(qtd_total - ocupados, 0)

    st.markdown(f"""
    <div class="rifa-grid-card">
        <div class="rifa-grid-head">
            <div>
                <h3>🎰 Mapa visual dos números</h3>
                <p>{ocupados}/{qtd_total} ocupados • {disponiveis} disponíveis</p>
            </div>
            <div class="rifa-legenda">
                <span><i class="rifa-dot disponivel"></i>Disponível</span>
                <span><i class="rifa-dot pago"></i>Pago</span>
                <span><i class="rifa-dot pendente"></i>Pendente/Reservado</span>
                <span><i class="rifa-dot vencedor"></i>Vencedor</span>
            </div>
        </div>
        <div class="rifa-grid">
            {''.join(blocos)}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_rifas_admin(clientes):
    st.markdown("""
    <div class="admin-work-card">
        <h3>🎟️ Rifas Automáticas GarageHub</h3>
        <p>Crie rifas no modo Normal, Top comprador, Top ganhador ou Híbrida, com mapa visual de números.</p>
    </div>
    """, unsafe_allow_html=True)

    try:
        rifas = buscar_rifas()
    except Exception as e:
        st.error("As tabelas de rifas ainda não existem no Supabase.")
        st.code(sql_rifas_necessario(), language="sql")
        st.caption(f"Detalhe técnico: {e}")
        return

    clientes_por_id = {str(c.get("id")): c for c in clientes}

    st.markdown("""
    <div class="feature-grid">
        <div class="feature-card"><h3>🎲 Normal</h3><p>Número comprado é sorteado automaticamente.</p></div>
        <div class="feature-card"><h3>💰 Top comprador</h3><p>Sem sorteio: vence quem comprou mais números.</p></div>
        <div class="feature-card"><h3>👑 Top ganhador</h3><p>Sem sorteio: vence quem lidera o histórico de vitórias.</p></div>
        <div class="feature-card"><h3>🔥 Híbrida</h3><p>Sorteio normal + Top comprador + Top ganhador.</p></div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("➕ Criar nova rifa", expanded=not bool(rifas)):
        with st.form("form_criar_rifa_garagehub"):
            r1, r2 = st.columns(2)

            with r1:
                r_titulo = st.text_input("Título da rifa", placeholder="Ex: Rifa Nissan Skyline RLC", key="rifa_titulo")
                r_premio = st.text_input("Mini / prêmio principal", placeholder="Ex: Hot Wheels RLC", key="rifa_premio")
                r_foto = st.file_uploader("Foto do prêmio", type=["jpg", "jpeg", "png"], key="rifa_foto")
                r_desc = st.text_area("Descrição", placeholder="Regras, observações e detalhes da campanha...", key="rifa_desc")

            with r2:
                r_valor = st.number_input("Valor por número", min_value=0.0, step=1.0, value=10.0, key="rifa_valor_numero")
                r_qtd = st.number_input("Quantidade de números", min_value=1, step=1, value=100, key="rifa_qtd_numeros")
                modos = {
                    "🎲 Sorteio normal": "sorteio_normal",
                    "💰 Top comprador": "top_comprador",
                    "👑 Top ganhador": "top_ganhador",
                    "🔥 Híbrida": "hibrida",
                }
                r_modo_label = st.selectbox("Modo de premiação", list(modos.keys()), key="rifa_modo")
                r_status = st.selectbox("Status", ["aberta", "pausada", "encerrada"], key="rifa_status")

            if st.form_submit_button("🚀 Criar rifa", use_container_width=True):
                if not r_titulo:
                    st.error("Informe o título da rifa.")
                else:
                    foto_url = upload_storage(r_foto, "rifas", r_titulo)
                    try:
                        criar_rifa(r_titulo, r_premio, foto_url, r_desc, r_valor, r_qtd, modos[r_modo_label], r_status)
                        st.success("Rifa criada com sucesso.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao criar rifa: {e}")

    total_rifas = len(rifas or [])
    rifas_abertas = len([r for r in rifas if str(r.get("status") or "") == "aberta"])
    rifas_sorteadas = len([r for r in rifas if str(r.get("status") or "") == "sorteada"])

    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(f'<div class="metric-card"><div class="metric-icon">🎟️</div><h2>{total_rifas}</h2><p>Total rifas</p></div>', unsafe_allow_html=True)
    with k2:
        st.markdown(f'<div class="metric-card"><div class="metric-icon">🟢</div><h2>{rifas_abertas}</h2><p>Abertas</p></div>', unsafe_allow_html=True)
    with k3:
        st.markdown(f'<div class="metric-card"><div class="metric-icon">🏁</div><h2>{rifas_sorteadas}</h2><p>Sorteadas</p></div>', unsafe_allow_html=True)

    if not rifas:
        st.info("Nenhuma rifa cadastrada ainda.")
        return

    st.divider()
    st.subheader("Rifas cadastradas")

    for rifa in rifas:
        rifa_id = rifa.get("id")
        try:
            numeros = buscar_numeros_rifa(rifa_id)
        except Exception:
            numeros = []

        qtd_total = int(rifa.get("qtd_numeros") or 0)
        vendidos = len(numeros)
        pagos = len([n for n in numeros if str(n.get("status_pagamento") or "").lower() == "pago"])
        elegiveis = len([n for n in numeros if str(n.get("status_pagamento") or "").lower() in ["pago", "reservado"]])
        arrecadado = pagos * float(rifa.get("valor_numero") or 0)
        progresso = int((vendidos / qtd_total) * 100) if qtd_total else 0
        foto = get_foto_item({"foto_url": rifa.get("premio_foto_url")})
        img = imagem_html(foto, "market-img") if foto else '<div class="market-empty">🎟️</div>'
        status = html.escape(str(rifa.get("status") or "aberta"))
        modo = modo_rifa_label(rifa.get("modo_premiacao"))

        st.markdown(f"""
        <div class="market-card hall-glow">
            {img}
            <div class="market-body">
                <div class="favorite-chip">🎟️</div>
                <h3 class="market-name">{html.escape(str(rifa.get('titulo') or 'Rifa GarageHub'))}</h3>
                <div class="market-tags">
                    <span class="market-tag market-tag-vip">{html.escape(modo)}</span>
                    <span class="market-tag market-tag-ok">{status}</span>
                </div>
                <p class="market-line"><b>Prêmio:</b> {html.escape(str(rifa.get('premio_nome') or '-'))}</p>
                <p class="market-line"><b>Descrição:</b> {html.escape(str(rifa.get('descricao') or '-'))}</p>
                <p class="market-line"><b>Como funciona:</b> {html.escape(rifa_modo_descricao(rifa.get('modo_premiacao')))}</p>
                <div class="market-price-grid">
                    <div class="market-price"><small>Números</small><strong>{vendidos}/{qtd_total}</strong></div>
                    <div class="market-price"><small>Elegíveis sorteio</small><strong>{elegiveis}</strong></div>
                    <div class="market-price"><small>Arrecadado pago</small><strong>{money(arrecadado)}</strong></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.progress(min(progresso, 100), text=f"{progresso}% dos números lançados")

        render_grade_numeros_rifa(rifa, numeros, clientes_por_id)

        if rifa.get("resultado_texto"):
            st.markdown(resultado_rifa_html(rifa, clientes_por_id), unsafe_allow_html=True)

        with st.expander(f"⚙️ Gerenciar rifa — {rifa.get('titulo')}", expanded=False):
            if not clientes:
                st.warning("Cadastre clientes antes de lançar números na rifa.")
            else:
                mapa_clientes = {f"{c.get('nome','')} — {c.get('email','')}": c for c in clientes}
                c1, c2 = st.columns([2, 1])

                with c1:
                    cliente_label = st.selectbox("Cliente comprador", list(mapa_clientes.keys()), key=f"rifa_cliente_{rifa_id}")
                with c2:
                    status_compra = st.selectbox("Status", ["pago", "pendente", "reservado"], key=f"rifa_status_compra_{rifa_id}")

                modo_lancamento = st.radio(
                    "Como lançar os números?",
                    ["Automático", "Escolher números específicos"],
                    horizontal=True,
                    key=f"rifa_modo_lancamento_{rifa_id}"
                )

                numeros_especificos = []
                qtd_compra = 1

                if modo_lancamento == "Automático":
                    qtd_compra = st.number_input(
                        "Qtd números automáticos",
                        min_value=1,
                        step=1,
                        value=1,
                        key=f"rifa_qtd_compra_{rifa_id}"
                    )
                    st.caption("O sistema pega os próximos números disponíveis automaticamente.")
                else:
                    texto_numeros = st.text_input(
                        "Números escolhidos pelo cliente",
                        placeholder="Ex: 7, 13, 22 ou 30-35",
                        key=f"rifa_numeros_especificos_{rifa_id}"
                    )
                    numeros_especificos = parse_numeros_especificos(texto_numeros)

                    if numeros_especificos:
                        st.caption(f"Números detectados: {', '.join(map(str, numeros_especificos[:40]))}" + (f" ... +{len(numeros_especificos)-40}" if len(numeros_especificos) > 40 else ""))
                    else:
                        st.caption("Digite números separados por vírgula, espaço ou faixa com hífen. Ex: 5, 8, 10-12")

                if st.button("➕ Lançar números para cliente", key=f"rifa_lancar_numeros_{rifa_id}", use_container_width=True):
                    cliente_sel = mapa_clientes[cliente_label]
                    ok, msg = registrar_numeros_rifa(
                        rifa,
                        cliente_sel.get("id"),
                        qtd_compra,
                        status_compra,
                        numeros_especificos=numeros_especificos
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.warning(msg)

            top_uid, top_qtd = calcular_top_comprador_rifa(numeros)
            if top_uid:
                st.info(f"🏆 Top comprador desta rifa: {nome_cliente_por_id(clientes_por_id, top_uid)} com {top_qtd} número(s).")

            if numeros:
                st.markdown("#### Números lançados")
                linhas = []
                for n in numeros[:80]:
                    linhas.append({
                        "Número": n.get("numero"),
                        "Cliente": nome_cliente_por_id(clientes_por_id, n.get("usuario_id")),
                        "Status": n.get("status_pagamento") or "pendente",
                    })
                st.dataframe(linhas, use_container_width=True, hide_index=True)
                if len(numeros) > 80:
                    st.caption(f"Mostrando 80 de {len(numeros)} números.")

                st.markdown("#### ✅ Confirmação de pagamento em lote")
                st.caption("Use esta área para confirmar como pago ou cancelar reservas/pendências de um cliente sem alterar número por número.")

                grupos_pagamento = agrupar_numeros_rifa_por_cliente_status(numeros)

                if not grupos_pagamento:
                    st.info("Ainda não há números para gerenciar em lote.")
                else:
                    for idx_grupo, grupo in enumerate(grupos_pagamento):
                        uid_grupo = grupo.get("usuario_id")
                        status_grupo = grupo.get("status") or "pendente"
                        numeros_grupo = sorted(grupo.get("numeros") or [])
                        qtd_grupo = len(numeros_grupo)
                        valor_grupo = qtd_grupo * float(rifa.get("valor_numero") or 0)
                        nome_grupo = nome_cliente_por_id(clientes_por_id, uid_grupo)
                        nums_txt = ", ".join(str(n).zfill(max(2, len(str(qtd_total)))) for n in numeros_grupo[:60])
                        if qtd_grupo > 60:
                            nums_txt += f" ... +{qtd_grupo - 60}"

                        st.markdown(f"""
                        <div class="pro-card hall-glow">
                            <h3>👤 {html.escape(str(nome_grupo))}</h3>
                            <p>
                                <strong>{qtd_grupo}</strong> número(s) • Status atual: <strong>{html.escape(str(status_grupo))}</strong><br>
                                Valor previsto: <strong>{money(valor_grupo)}</strong><br>
                                Números: {html.escape(nums_txt)}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

                        col_pg_1, col_pg_2, col_pg_3 = st.columns([1, 1, 1.2])

                        with col_pg_1:
                            if st.button(
                                "✅ Marcar este lote como pago",
                                key=f"rifa_lote_pago_{rifa_id}_{uid_grupo}_{status_grupo}_{idx_grupo}",
                                use_container_width=True
                            ):
                                try:
                                    atualizar_numeros_rifa_lote(rifa_id, uid_grupo, status_grupo, "pago")
                                    st.success("Lote marcado como pago.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao confirmar pagamento do lote: {e}")

                        with col_pg_2:
                            if st.button(
                                "🔵 Voltar para reservado",
                                key=f"rifa_lote_reservado_{rifa_id}_{uid_grupo}_{status_grupo}_{idx_grupo}",
                                use_container_width=True
                            ):
                                try:
                                    atualizar_numeros_rifa_lote(rifa_id, uid_grupo, status_grupo, "reservado")
                                    st.success("Lote marcado como reservado.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao reservar lote: {e}")

                        with col_pg_3:
                            confirmar_cancelamento_lote = st.checkbox(
                                "Confirmar cancelamento/remover números",
                                key=f"rifa_lote_confirmar_cancelar_{rifa_id}_{uid_grupo}_{status_grupo}_{idx_grupo}"
                            )
                            if st.button(
                                "🗑️ Cancelar lote e liberar números",
                                key=f"rifa_lote_cancelar_{rifa_id}_{uid_grupo}_{status_grupo}_{idx_grupo}",
                                use_container_width=True
                            ):
                                if not confirmar_cancelamento_lote:
                                    st.warning("Marque a confirmação antes de cancelar o lote.")
                                else:
                                    try:
                                        excluir_numeros_rifa_lote(rifa_id, uid_grupo, status_grupo)
                                        st.success("Lote cancelado e números liberados.")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao cancelar lote: {e}")

            st.divider()
            st.markdown("### 🎲 Área oficial do sorteio")
            st.caption("O sorteio usa somente números com status pago ou reservado. No modo Top comprador/Top ganhador, o botão apura o ranking e grava o resultado oficial.")

            if str(rifa.get("status") or "") == "sorteada":
                st.success("Esta rifa já foi sorteada/apurada. O resultado oficial está gravado acima.")
            elif elegiveis <= 0 and str(rifa.get("modo_premiacao") or "") in ["sorteio_normal", "hibrida", "sorteio_top_comprador", "sorteio_top_ganhador"]:
                st.warning("Ainda não há números pagos/reservados suficientes para realizar o sorteio.")

            confirmar_sorteio = st.checkbox(
                "Confirmo que quero realizar/apurar esta rifa agora",
                key=f"rifa_confirmar_sorteio_{rifa_id}"
            )

            ac1, ac2, ac3 = st.columns(3)
            with ac1:
                if st.button(
                    "🎲 Realizar sorteio agora",
                    key=f"rifa_processar_{rifa_id}",
                    use_container_width=True,
                    disabled=(str(rifa.get("status")) == "sorteada" or not confirmar_sorteio)
                ):
                    ok, msg = processar_resultado_rifa(rifa, numeros, clientes, rifas)
                    if ok:
                        st.balloons()
                        st.success(msg)
                        st.rerun()
                    else:
                        st.warning(msg)
            with ac2:
                novo_status = st.selectbox(
                    "Alterar status",
                    ["aberta", "pausada", "encerrada", "sorteada"],
                    index=["aberta", "pausada", "encerrada", "sorteada"].index(str(rifa.get("status") or "aberta")) if str(rifa.get("status") or "aberta") in ["aberta", "pausada", "encerrada", "sorteada"] else 0,
                    key=f"rifa_novo_status_{rifa_id}"
                )
                if st.button("💾 Salvar status", key=f"rifa_salvar_status_{rifa_id}", use_container_width=True):
                    atualizar_rifa(rifa_id, {"status": novo_status})
                    st.success("Status atualizado.")
                    st.rerun()
            with ac3:
                confirmar = st.checkbox("Confirmar exclusão", key=f"rifa_confirmar_excluir_{rifa_id}")
                if st.button("🗑️ Excluir rifa", key=f"rifa_excluir_{rifa_id}", use_container_width=True):
                    if not confirmar:
                        st.warning("Confirme antes de excluir.")
                    else:
                        excluir_rifa(rifa_id)
                        st.success("Rifa excluída.")
                        st.rerun()

    st.divider()
    st.subheader("👑 Ranking geral de ganhadores")
    top_ganhador_uid, top_ganhador_qtd = calcular_top_ganhador_geral(rifas)
    if top_ganhador_uid:
        st.markdown(f"""
        <div class="pro-card hall-glow">
            <h3>👑 Top ganhador geral</h3>
            <p><strong>{html.escape(nome_cliente_por_id(clientes_por_id, top_ganhador_uid))}</strong><br>{top_ganhador_qtd} vitória(s) registradas nas rifas.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Ainda não há histórico de ganhadores. Depois da primeira rifa sorteada, o ranking começa a aparecer aqui.")



def render_rifas_cliente(usuario):
    """Área de rifas para cliente comum visualizar campanhas abertas e seus números."""
    st.markdown("""
    <div class="market-hero">
        <div class="market-kicker">🎟️ Rifas GarageHub</div>
        <h1 class="market-title">Rifas abertas da comunidade</h1>
        <p class="market-desc">Veja os prêmios, acompanhe o mapa visual dos números e confira quais números já estão reservados ou pagos.</p>
        <div class="market-stats">
            <div class="market-stat"><strong>🎲</strong><small>sorteio normal</small></div>
            <div class="market-stat"><strong>💰</strong><small>top comprador</small></div>
            <div class="market-stat"><strong>👑</strong><small>top ganhador</small></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_rifa_refresh_1, col_rifa_refresh_2 = st.columns([3, 1])
    with col_rifa_refresh_1:
        st.caption(f"Última atualização da tela: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    with col_rifa_refresh_2:
        if st.button("🔄 Atualizar rifas", use_container_width=True, key="cliente_atualizar_rifas"):
            st.rerun()

    try:
        rifas = buscar_rifas()
    except Exception as e:
        st.error("As rifas ainda não estão disponíveis. Avise o admin para conferir as tabelas no Supabase.")
        st.caption(f"Detalhe técnico: {e}")
        return

    try:
        usuarios_rifas = listar_usuarios()
    except Exception:
        usuarios_rifas = []

    clientes_por_id = {str(c.get("id")): c for c in usuarios_rifas}

    rifas_visiveis = [
        r for r in (rifas or [])
        if str(r.get("status") or "").lower() in ["aberta", "pausada", "encerrada", "sorteada"]
    ]

    if not rifas_visiveis:
        st.info("Ainda não há rifas disponíveis para clientes.")
        return

    for rifa in rifas_visiveis:
        rifa_id = rifa.get("id")

        try:
            numeros = buscar_numeros_rifa_fresco(rifa_id)
        except Exception:
            numeros = []

        qtd_total = int(rifa.get("qtd_numeros") or 0)
        vendidos = len(numeros)
        pagos = len([n for n in numeros if str(n.get("status_pagamento") or "").lower() == "pago"])
        reservados = len([n for n in numeros if str(n.get("status_pagamento") or "").lower() == "reservado"])
        disponiveis = max(qtd_total - vendidos, 0)
        progresso = int((vendidos / qtd_total) * 100) if qtd_total else 0
        resumo_sync = f"Sincronizado com Supabase: {vendidos} número(s) carregado(s) nesta rifa."

        meus_numeros = [
            n for n in numeros
            if str(n.get("usuario_id")) == str(usuario.get("id"))
        ]

        foto = get_foto_item({"foto_url": rifa.get("premio_foto_url")})
        img = imagem_html(foto, "market-img") if foto else '<div class="market-empty">🎟️</div>'
        status = html.escape(str(rifa.get("status") or "aberta"))
        modo = modo_rifa_label(rifa.get("modo_premiacao"))

        st.markdown(f"""
        <div class="market-card hall-glow">
            {img}
            <div class="market-body">
                <div class="favorite-chip">🎟️</div>
                <h3 class="market-name">{html.escape(str(rifa.get('titulo') or 'Rifa GarageHub'))}</h3>
                <div class="market-tags">
                    <span class="market-tag market-tag-vip">{html.escape(modo)}</span>
                    <span class="market-tag market-tag-ok">{status}</span>
                </div>
                <p class="market-line"><b>Prêmio:</b> {html.escape(str(rifa.get('premio_nome') or '-'))}</p>
                <p class="market-line"><b>Descrição:</b> {html.escape(str(rifa.get('descricao') or '-'))}</p>
                <p class="market-line"><b>Como funciona:</b> {html.escape(rifa_modo_descricao(rifa.get('modo_premiacao')))}</p>
                <div class="market-price-grid">
                    <div class="market-price"><small>Valor número</small><strong>{money(rifa.get('valor_numero') or 0)}</strong></div>
                    <div class="market-price"><small>Números</small><strong>{vendidos}/{qtd_total}</strong></div>
                    <div class="market-price"><small>Disponíveis</small><strong>{disponiveis}</strong></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.progress(min(progresso, 100), text=f"{progresso}% dos números ocupados")
        st.caption(resumo_sync)

        # =========================
        # RESUMO DAS COTAS DO CLIENTE
        # =========================
        qtd_minhas_cotas = len(meus_numeros)
        minhas_pagas = len([
            n for n in meus_numeros
            if str(n.get("status_pagamento") or "").lower() == "pago"
        ])
        minhas_reservadas = len([
            n for n in meus_numeros
            if str(n.get("status_pagamento") or "").lower() == "reservado"
        ])
        minhas_pendentes = len([
            n for n in meus_numeros
            if str(n.get("status_pagamento") or "").lower() in ["pendente", "aguardando_pix"]
        ])
        total_investido_cliente = qtd_minhas_cotas * float(rifa.get("valor_numero") or 0)
        total_pago_cliente = minhas_pagas * float(rifa.get("valor_numero") or 0)

        st.markdown(f"""
        <div class="pro-grid">
            <div class="pro-card hall-glow">
                <h3>🎟️ Suas cotas</h3>
                <p><strong>{qtd_minhas_cotas}</strong><br>Total de números vinculados a você nesta rifa.</p>
            </div>
            <div class="pro-card hall-glow">
                <h3>💰 Total investido</h3>
                <p><strong>{money(total_investido_cliente)}</strong><br>Valor total das suas cotas nesta rifa.</p>
            </div>
            <div class="pro-card hall-glow">
                <h3>✅ Pago confirmado</h3>
                <p><strong>{money(total_pago_cliente)}</strong><br>{minhas_pagas} cota(s) paga(s).</p>
            </div>
        </div>
        <div class="pro-grid">
            <div class="pro-card">
                <h3>🟢 Pagas</h3>
                <p><strong>{minhas_pagas}</strong><br>Cotas confirmadas pelo admin.</p>
            </div>
            <div class="pro-card">
                <h3>🔵 Reservadas</h3>
                <p><strong>{minhas_reservadas}</strong><br>Cotas separadas para você.</p>
            </div>
            <div class="pro-card">
                <h3>🟡 Pendentes</h3>
                <p><strong>{minhas_pendentes}</strong><br>Aguardando confirmação.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if meus_numeros:
            lista_meus = ", ".join(str(n.get("numero")).zfill(max(2, len(str(qtd_total)))) for n in meus_numeros)
            st.success(f"Seus números nesta rifa: {lista_meus}")
        else:
            st.info("Você ainda não possui números nesta rifa. Peça para o admin reservar ou lançar seus números.")

        render_grade_numeros_rifa(rifa, numeros, clientes_por_id)

        if rifa.get("resultado_texto"):
            st.markdown(resultado_rifa_html(rifa, clientes_por_id), unsafe_allow_html=True)

        with st.expander("📋 Resumo da rifa", expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Pagos", pagos)
            with c2:
                st.metric("Reservados", reservados)
            with c3:
                st.metric("Disponíveis", disponiveis)

            if numeros:
                linhas = []
                for n in numeros:
                    linhas.append({
                        "Número": n.get("numero"),
                        "Status": n.get("status_pagamento") or "pendente",
                        "Cliente": nome_cliente_por_id(clientes_por_id, n.get("usuario_id")),
                    })
                st.dataframe(linhas, use_container_width=True, hide_index=True)



# =========================
# ESTADO
# =========================
if "usuario" not in st.session_state:
    st.session_state.usuario = None
if "editar_mini_id" not in st.session_state:
    st.session_state.editar_mini_id = None


# =========================
# TOPO / HERO
# =========================
if banner_b64:
    st.markdown(f"""
    <div class="hero">
        <div style="display:flex; gap:28px; align-items:center; flex-wrap:wrap;">
            <img src="data:image/jpeg;base64,{banner_b64}" class="hero-img">
            <div>
                <h1 class="hero-title">🏁 GarageHub</h1>
                <p class="hero-sub">Comunidade Garagem Hot Wheels</p>
                <p class="hero-desc">Garagem digital, carteirinha de membro, controle de coleção e valorização das miniaturas.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="hero">
        <h1 class="hero-title">🏁 GarageHub</h1>
        <p class="hero-sub">Comunidade Garagem Hot Wheels</p>
        <p class="hero-desc">Garagem digital, carteirinha de membro, controle de coleção e valorização das miniaturas.</p>
    </div>
    """, unsafe_allow_html=True)


# =========================
# LOGIN / CADASTRO
# =========================
if st.session_state.usuario is None:
    aba_login, aba_cadastro = st.tabs(["Entrar", "Criar conta"])

    with aba_login:
        _l, login_col, _r = st.columns([0.85, 1.15, 0.85])
        with login_col:
            st.markdown("""
            <div class="login-shell">
                <div class="login-kicker">🏁 Acesso exclusivo</div>
                <h2>Entrar na garagem</h2>
                <p>Acesse sua carteirinha, coleção, métricas e painel GarageHub em um ambiente premium para colecionadores.</p>
                <div class="login-mini-stats">
                    <div class="login-mini-stat"><strong>GHW</strong><small>Comunidade</small></div>
                    <div class="login-mini-stat"><strong>VIP</strong><small>Carteirinha</small></div>
                    <div class="login-mini-stat"><strong>1:64</strong><small>Garagem</small></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            lembrar_login = st.checkbox(
                "Lembrar meu e-mail neste navegador",
                value=True,
                key="login_lembrar_email"
            )

            injetar_melhorias_login_browser(lembrar_login)

            email = st.text_input(
                "E-mail",
                key="login_email",
                placeholder="seuemail@exemplo.com"
            )

            senha = st.text_input(
                "Senha",
                type="password",
                key="login_senha",
                placeholder="Digite sua senha"
            )

            col_login_1, col_login_2, col_login_3 = st.columns(3)

            with col_login_1:
                entrar = st.button("Entrar na GarageHub", use_container_width=True)

            with col_login_2:
                primeiro_acesso = st.button("🔐 Primeiro acesso", use_container_width=True)

            with col_login_3:
                esqueci_senha = st.button("🔁 Esqueci minha senha", use_container_width=True)

            if esqueci_senha:
                if not email:
                    st.error("Informe seu e-mail para recuperar a senha.")
                    st.stop()

                usuario = buscar_usuario_por_email(email)

                if not usuario:
                    st.error("E-mail não encontrado. Peça ao admin para corrigir seu cadastro.")
                    st.stop()

                try:
                    resetar_senha_cliente(usuario["id"])
                    usuario["senha"] = "primeiro_acesso"
                    st.session_state["usuario_primeiro_acesso"] = usuario
                    st.success("Senha resetada. Agora crie uma nova senha.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao resetar senha: {e}")
                    st.stop()

            if primeiro_acesso:
                if not email:
                    st.error("Informe seu e-mail.")
                    st.stop()

                usuario = buscar_usuario_por_email(email)

                if not usuario:
                    st.error("E-mail não encontrado. Peça ao admin para corrigir seu cadastro.")
                    st.stop()

                if senha_pendente(usuario):
                    st.session_state["usuario_primeiro_acesso"] = usuario
                    st.rerun()

                st.info("Sua conta já possui senha cadastrada. Use sua senha para entrar.")

            if entrar:
                if not email:
                    st.error("Informe seu e-mail.")
                    st.stop()

                usuario = buscar_usuario_por_email(email)

                if not usuario:
                    st.error("E-mail não encontrado.")
                    st.stop()

                if senha_pendente(usuario):
                    st.session_state["usuario_primeiro_acesso"] = usuario
                    st.rerun()

                usuario = login(email, senha)

                if usuario:
                    if lembrar_login:
                        st.session_state["ultimo_email_login"] = str(email or "").strip().lower()
                    else:
                        st.session_state.pop("ultimo_email_login", None)

                    st.session_state["usuario"] = usuario
                    st.rerun()
                else:
                    st.error("E-mail ou senha inválidos.")


    with aba_cadastro:
        _l, cad_col, _r = st.columns([0.35, 1.5, 0.35])
        with cad_col:
            st.markdown("""
            <div class="login-shell">
                <div class="login-kicker">👤 Cadastro normal</div>
                <h2>Criar conta</h2>
                <p>Crie sua conta como cliente comum. O status de Membro VIP é concedido exclusivamente pelo admin.</p>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            with col1:
                nome = st.text_input("Nome completo", key="cad_nome", placeholder="Seu nome")
                novo_email = st.text_input("E-mail para cadastro", key="cad_email", placeholder="seuemail@exemplo.com")
                nova_senha = st.text_input("Senha", type="password", key="cad_senha", placeholder="Crie uma senha")
                telefone = st.text_input("Telefone / WhatsApp", key="cad_telefone", placeholder="(11) 99999-9999")

            with col2:
                cidade = st.text_input("Cidade", key="cad_cidade", placeholder="Sua cidade")
                estado = st.text_input("Estado", key="cad_estado", placeholder="SP")
                instagram = st.text_input("Instagram", key="cad_instagram", placeholder="@seuinstagram")

            foto_perfil = st.file_uploader("Foto de perfil", type=["jpg", "jpeg", "png"], key="cad_foto_perfil")

            if st.button("Criar minha garagem", key="btn_cadastro", use_container_width=True):
                foto_url = upload_perfil_avatar(foto_perfil, "perfis", novo_email)
                ok, msg = criar_usuario(nome, novo_email, nova_senha, telefone, cidade, estado, instagram, foto_url)
                if ok:
                    usuario_criado = buscar_usuario_por_email(novo_email)
                    if usuario_criado:
                        st.session_state["usuario"] = usuario_criado
                        st.success("Conta criada com sucesso. Entrando na sua garagem...")
                        st.rerun()
                    else:
                        st.success(msg)
                        st.info("Conta criada. Faça login com seu e-mail e senha.")
                else:
                    st.error(msg)

# =========================
# ÁREA LOGADA
# =========================
else:
    usuario = st.session_state.usuario

    render_sidebar_saas(usuario)

    col_top1, col_top2 = st.columns([4, 1])
    with col_top1:
        st.markdown(f"### Bem-vindo, {html.escape(usuario.get('nome', ''))}")
    with col_top2:
        if st.button("Sair", key="btn_sair"):
            st.session_state.usuario = None
            st.session_state.editar_mini_id = None
            st.rerun()

    # =========================
    # ADMIN
    # =========================
    if usuario.get("tipo") == "admin":
        st.markdown('<span class="admin-pill">PAINEL ADM</span>', unsafe_allow_html=True)
        st.markdown("""
        <div class="admin-panel-title">
            <div>
                <h2>Painel administrativo</h2>
                <p>Clientes, pedidos, minis, pagamentos e controle da comunidade.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Visual mais limpo: removemos os cards conceituais grandes para o painel ficar direto ao ponto.
        usuarios = listar_usuarios()
        clientes = [u for u in usuarios if u.get("tipo") != "admin"]
        todas_minis = buscar_todas_minis()

        total = len(usuarios)
        ativos = len([u for u in usuarios if u.get("status") == "ativo"])
        bloqueados = len([u for u in usuarios if u.get("status") == "bloqueado"])
        novos_1d = contar_cadastros_novos(usuarios, 1)
        novos_3d = contar_cadastros_novos(usuarios, 3)
        novos_7d = contar_cadastros_novos(usuarios, 7)

        total_pago_fin = sum(float(m.get("valor_pago") or 0) for m in todas_minis if (m.get("status_pagamento") or "pendente") == "pago")
        total_pendente_fin = sum(float(m.get("valor_pago") or 0) for m in todas_minis if (m.get("status_pagamento") or "pendente") == "pendente")
        total_reservado_fin = sum(float(m.get("valor_pago") or 0) for m in todas_minis if (m.get("status_pagamento") or "pendente") == "reservado")

        st.markdown(f"""
        <style>
        .admin-compact-panel {{
            background: linear-gradient(145deg, rgba(15,23,42,.82), rgba(2,6,23,.96));
            border: 1px solid rgba(250,204,21,.20);
            border-radius: 24px;
            padding: 18px;
            margin: 10px 0 18px;
            box-shadow: 0 18px 42px rgba(0,0,0,.28);
        }}
        .admin-compact-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
        }}
        .admin-compact-card {{
            background: rgba(15,23,42,.78);
            border: 1px solid rgba(148,163,184,.16);
            border-radius: 18px;
            padding: 14px 16px;
            min-height: 92px;
        }}
        .admin-compact-card small {{
            color: #94a3b8;
            font-weight: 950;
            text-transform: uppercase;
            letter-spacing: .3px;
            font-size: 11px;
        }}
        .admin-compact-card strong {{
            display: block;
            margin-top: 8px;
            color: #f8fafc;
            font-size: 30px;
            font-weight: 950;
            line-height: 1;
        }}
        .admin-compact-card span {{
            display: block;
            margin-top: 7px;
            color: #cbd5e1;
            font-size: 12px;
            font-weight: 800;
        }}
        .admin-new-strip {{
            margin-top: 12px;
            background: rgba(2,6,23,.42);
            border: 1px solid rgba(56,189,248,.16);
            border-radius: 18px;
            padding: 13px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .admin-new-strip b {{ color: #facc15; }}
        .admin-new-pills {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .admin-new-pill {{
            background: rgba(250,204,21,.10);
            border: 1px solid rgba(250,204,21,.28);
            border-radius: 999px;
            padding: 8px 12px;
            color: #fde68a;
            font-weight: 950;
            font-size: 13px;
        }}
        @media (max-width: 900px) {{
            .admin-compact-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        }}
        @media (max-width: 560px) {{
            .admin-compact-grid {{ grid-template-columns: 1fr; }}
        }}
        </style>

        <div class="admin-compact-panel">
            <div class="admin-compact-grid">
                <div class="admin-compact-card"><small>👥 Total usuários</small><strong>{total}</strong><span>Inclui admin e clientes</span></div>
                <div class="admin-compact-card"><small>👤 Clientes</small><strong>{len(clientes)}</strong><span>Cadastros de colecionadores</span></div>
                <div class="admin-compact-card"><small>✅ Ativos</small><strong>{ativos}</strong><span>Usuários liberados</span></div>
                <div class="admin-compact-card"><small>💰 Pago</small><strong>{money(total_pago_fin)}</strong><span>Total pago na garagem</span></div>
            </div>
            <div class="admin-new-strip">
                <div><b>🆕 Novos cadastros</b><br><span style="color:#94a3b8;font-weight:800;font-size:13px;">Resumo rápido para acompanhar crescimento sem poluir o painel.</span></div>
                <div class="admin-new-pills">
                    <div class="admin-new-pill">1 dia: {novos_1d}</div>
                    <div class="admin-new-pill">3 dias: {novos_3d}</div>
                    <div class="admin-new-pill">7 dias: {novos_7d}</div>
                    <div class="admin-new-pill">Bloqueados: {bloqueados}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        render_alertas_financeiros_admin(todas_minis, clientes)

        aba_clientes, aba_loja, aba_pre_venda_admin, aba_pedidos, aba_minis, aba_financeiro, aba_hall_admin, aba_ranking_admin, aba_timeline_admin, aba_sorteios_admin, aba_lab_admin, aba_exec_admin, aba_checkout_admin, aba_notif_admin = st.tabs([
            "👥 Clientes",
            "🛒 Loja",
            "🚧 Pré-venda",
            "💰 Pedidos",
            "🏎️ Minis",
            "📊 Financeiro",
            "🏆 Hall",
            "👑 Ranking",
            "🕒 Timeline",
            "🎟️ Sorteios",
            "🧪 Lab IA/Pix",
            "🚀 Executivo",
            "💳 Checkout",
            "🔔 Notificações"
        ])

        # =========================
        # ABA CLIENTES
        # =========================
        with aba_clientes:
            st.markdown("""
            <div class="admin-work-card">
                <h3>➕ Criar cliente</h3>
                <p>Utilize este cadastro manual quando o cliente comprou sem possuir uma conta.</p>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("Abrir cadastro rápido de cliente", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    adm_nome = st.text_input("Nome do cliente", key="adm_cliente_nome")
                    adm_email = st.text_input("E-mail do cliente", key="adm_cliente_email")
                    adm_senha = st.text_input("Senha inicial", value="123456", type="password", key="adm_cliente_senha")
                    adm_tel = st.text_input("Telefone / WhatsApp", key="adm_cliente_tel")
                with c2:
                    adm_cidade = st.text_input("Cidade", key="adm_cliente_cidade")
                    adm_estado = st.text_input("Estado", key="adm_cliente_estado")
                    adm_insta = st.text_input("Instagram", key="adm_cliente_insta")
                    adm_foto = st.file_uploader("Foto do cliente", type=["jpg", "jpeg", "png"], key="adm_cliente_foto")

                if st.button("Criar cliente", key="btn_criar_cliente_admin"):
                    foto_cliente = upload_perfil_avatar(adm_foto, "perfis", adm_email)
                    ok, msg = criar_cliente_admin(adm_nome, adm_email, adm_senha, adm_tel, adm_cidade, adm_estado, adm_insta, foto_cliente)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

            if st.session_state.get("admin_cliente_garagem_id"):
                cliente_id_aberto = st.session_state.get("admin_cliente_garagem_id")

                # Primeiro tenta pela lista já carregada; se for cadastro novo e a lista ainda
                # estiver stale, busca direto no Supabase pelo ID para a garagem abrir mesmo vazia.
                cliente_aberto = next(
                    (u for u in usuarios if str(u.get("id")) == str(cliente_id_aberto)),
                    None
                )

                if not cliente_aberto:
                    cliente_aberto = buscar_usuario_por_id(cliente_id_aberto)

                if cliente_aberto:
                    render_admin_garagem_cliente(cliente_aberto)
                    st.info("Você está visualizando a garagem do cliente. Para trocar de aba, use as abas acima normalmente; para voltar à lista, clique em Voltar para usuários.")
                    st.divider()
                else:
                    st.session_state.pop("admin_cliente_garagem_id", None)
                    st.warning("Cliente não encontrado. Clique em Atualizar cadastros e tente novamente.")
                    st.rerun()

            col_refresh_usuarios, _ = st.columns([1, 4])
            with col_refresh_usuarios:
                if st.button("🔄 Atualizar cadastros", use_container_width=True, key="btn_atualizar_clientes_admin"):
                    st.rerun()

            # Recarrega a lista ao entrar na aba para novos cadastros aparecerem no admin.
            usuarios = listar_usuarios()
            clientes = [u for u in usuarios if u.get("tipo") != "admin"]

            st.subheader("Usuários cadastrados")
            st.caption(f"Novos cadastros: {contar_cadastros_novos(usuarios, 1)} em 1 dia • {contar_cadastros_novos(usuarios, 3)} em 3 dias • {contar_cadastros_novos(usuarios, 7)} em 7 dias")

            for u in usuarios:
                status = str(u.get("status", "ativo") or "ativo")
                tipo = str(u.get("tipo", "usuario") or "usuario")
                status_class = "status-ativo" if status == "ativo" else "status-bloqueado"
                tipo_class = "type-admin" if tipo == "admin" else "type-usuario"
                instagram_user = str(u.get("instagram", "") or "-")
                if instagram_user != "-" and not instagram_user.startswith("@"):
                    instagram_user = f"@{instagram_user}"

                col_foto, col_dados = st.columns([1, 5], gap="large")
                with col_foto:
                    st.markdown('<div class="admin-avatar-wrap">' + perfil_html(get_foto_perfil_usuario(u), u.get('nome', '')) + '</div>', unsafe_allow_html=True)
                with col_dados:
                    st.markdown(f"""
                    <div class="user-card">
                        <div class="user-head">
                            <div>
                                <div class="user-name">{html.escape(str(u.get('nome', '')))}</div>
                                <div class="user-email">{html.escape(str(u.get('email', '')))}</div>
                            </div>
                            <div>
                                <span class="status-pill {status_class}">{html.escape(status)}</span>
                                <span class="type-pill {tipo_class}">{html.escape(tipo)}</span>
                                <span class="type-pill {'badge-vip' if (u.get('nivel_cliente') or 'comum') == 'vip' else 'badge-comum'}">{html.escape('VIP' if (u.get('nivel_cliente') or 'comum') == 'vip' else 'Comum')}</span>
                            </div>
                        </div>
                        <div class="user-info-grid">
                            <div class="user-info-item"><small>Telefone</small><strong>{html.escape(str(u.get('telefone', '') or '-'))}</strong></div>
                            <div class="user-info-item"><small>Cidade / Estado</small><strong>{html.escape(str(u.get('cidade', '') or '-'))} / {html.escape(str(u.get('estado', '') or '-'))}</strong></div>
                            <div class="user-info-item"><small>Instagram</small><strong>{html.escape(instagram_user)}</strong></div>
                            <div class="user-info-item"><small>Carteirinha</small><strong>{html.escape(str(u.get('codigo_membro', '') or '-'))}</strong></div>
                            <div class="user-info-item"><small>Perfil</small><strong>{html.escape(tipo.upper())}</strong></div>
                            <div class="user-info-item"><small>Situação</small><strong>{html.escape(status.upper())}</strong></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                    with c1:
                        if st.button("✅ Liberar", key=f"liberar_{u['id']}"):
                            atualizar_status(u["id"], "ativo")
                            st.rerun()
                    with c2:
                        if st.button("🔒 Bloquear", key=f"bloquear_{u['id']}"):
                            atualizar_status(u["id"], "bloqueado")
                            st.rerun()
                    with c3:
                        if u.get("tipo") != "admin":
                            nivel_atual = u.get("nivel_cliente") or "comum"
                            if nivel_atual == "vip":
                                if st.button("Remover VIP", key=f"vip_remover_{u['id']}"):
                                    try:
                                        atualizar_nivel_cliente(u["id"], "comum")
                                        st.rerun()
                                    except Exception:
                                        st.error("Campo nivel_cliente não existe. Rode o SQL informado.")
                            else:
                                if st.button("Conceder VIP", key=f"vip_conceder_{u['id']}"):
                                    try:
                                        atualizar_nivel_cliente(u["id"], "vip")
                                        st.rerun()
                                    except Exception:
                                        st.error("Campo nivel_cliente não existe. Rode o SQL informado.")

                    with c4:
                        if u.get("tipo") != "admin":
                            if st.button("🚗 Abrir garagem", key=f"abrir_garagem_{u['id']}"):
                                st.session_state["admin_cliente_garagem_id"] = u["id"]
                                st.rerun()

                    if u.get("tipo") != "admin":
                        with st.expander("🗑️ Excluir cliente definitivamente", expanded=False):
                            st.warning(
                                "Atenção: esta ação apaga o cliente, as minis, os pedidos e logs vinculados. "
                                "Depois de confirmar, não tem volta."
                            )

                            texto_confirmacao = st.text_input(
                                "Digite EXCLUIR para confirmar",
                                key=f"texto_excluir_cliente_{u['id']}"
                            )

                            confirmar_excluir_cliente = st.checkbox(
                                "Confirmo que quero excluir este cliente definitivamente",
                                key=f"confirmar_excluir_cliente_{u['id']}"
                            )

                            if st.button(
                                "🗑️ Excluir cliente",
                                key=f"excluir_cliente_{u['id']}",
                                use_container_width=True
                            ):
                                if not confirmar_excluir_cliente or texto_confirmacao.strip().upper() != "EXCLUIR":
                                    st.error("Para excluir, marque a confirmação e digite EXCLUIR.")
                                else:
                                    ok, msg = excluir_cliente_completo(u["id"])
                                    if ok:
                                        if str(st.session_state.get("admin_cliente_garagem_id")) == str(u["id"]):
                                            st.session_state.pop("admin_cliente_garagem_id", None)
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)

                    with st.expander("🖼️ Alterar foto do usuário", expanded=False):
                        foto_salva_atual = get_foto_perfil_usuario(u)
                        if foto_salva_atual:
                            st.caption("Foto atual cadastrada no perfil.")
                        else:
                            st.caption("Ainda não há foto cadastrada neste perfil.")

                        nova_foto_usuario_admin = st.file_uploader(
                            "Enviar nova foto",
                            type=["jpg", "jpeg", "png"],
                            key=f"admin_upload_foto_usuario_{u['id']}"
                        )

                        if st.button("💾 Salvar foto do usuário", key=f"admin_salvar_foto_usuario_{u['id']}", use_container_width=True):
                            if nova_foto_usuario_admin is None:
                                st.warning("Escolha uma imagem primeiro.")
                            else:
                                foto_url = upload_perfil_avatar(
                                    nova_foto_usuario_admin,
                                    "perfis",
                                    f"admin_perfil_{u['id']}"
                                )
                                atualizar_foto_perfil(u["id"], foto_url)
                                u["foto_perfil_url"] = foto_url
                                u["foto_url"] = foto_url
                                st.success("Foto atualizada. Ela aparecerá no círculo do perfil.")
                                st.rerun()

        # =========================
        # ABA LOJA
        # =========================
        with aba_loja:
            st.markdown("""
            <div class="admin-work-card">
                <h3>🛒 Loja — minis disponíveis para venda</h3>
                <p>Cadastre aqui os minis que aparecem na aba Loja para todos os clientes. Cliente não cadastra mini; admin lança compra/presente na garagem oficial.</p>
            </div>
            """, unsafe_allow_html=True)

            st.caption("📸 Novas fotos da Loja serão salvas em qualidade original no Supabase Storage. O banco guarda apenas o link, evitando timeout.")

            with st.expander("🏁 Cadastrar mini na loja", expanded=False):
                st.markdown("### 🛒 Novo mini para marketplace")
                with st.form("form_admin_loja_mini"):
                    l1, l2 = st.columns(2)
                    with l1:
                        loja_nome = st.text_input("Nome da mini", key="loja_nome")
                        loja_marca = st.text_input("Marca", value="Hot Wheels", key="loja_marca")
                        loja_serie = st.text_input("Série", key="loja_serie")
                        loja_ano = st.text_input("Ano", key="loja_ano")
                        loja_foto = st.file_uploader("Foto da mini", type=["jpg", "jpeg", "png"], key="loja_foto")
                    with l2:
                        loja_categoria = st.selectbox("Categoria da loja", CATEGORIAS_LOJA, key="loja_categoria")
                        loja_raridade = st.selectbox("Raridade", ["Comum", "TH", "STH", "Premium", "RLC", "Chase", "Especial"], key="loja_raridade")
                        loja_valor = st.number_input("Preço de venda", min_value=0.0, step=1.0, key="loja_valor")
                        loja_estimado = st.number_input("Valor estimado", min_value=0.0, step=1.0, key="loja_estimado")
                        loja_estoque = st.number_input("Disponíveis em estoque", min_value=0, step=1, value=1, key="loja_estoque")
                        loja_status = st.selectbox("Status na loja", ["disponivel", "reservado", "vendido"], key="loja_status")
                        loja_destaque = st.text_input("Destaque", placeholder="Ex: Novidade, Raro, Promoção", key="loja_destaque")

                    if st.form_submit_button("Publicar mini na loja"):
                        if not loja_nome:
                            st.error("Informe o nome da mini.")
                        else:
                            loja_foto_url = upload_storage_loja(loja_foto, loja_nome)
                            try:
                                loja_status_final = "vendido" if int(loja_estoque or 0) <= 0 else "disponivel"
                                loja_destaque_final = atualizar_destaque_com_qtd_e_categoria(loja_destaque, loja_estoque, loja_categoria)
                                cadastrar_loja_mini(loja_nome, loja_marca, loja_serie, loja_ano, loja_raridade, loja_valor, loja_estimado, loja_foto_url, loja_status_final, loja_destaque_final)
                                st.success("Mini publicada na loja.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Não foi possível salvar na loja. Erro real: {e}")

            st.subheader("Minis cadastradas na loja")
            try:
                loja_minis_admin = buscar_loja_minis(apenas_disponiveis=False)
            except Exception as e:
                loja_minis_admin = []
                st.error(f"Erro real ao carregar a loja_minis: {e}")
                st.info("A tabela loja_minis já foi confirmada no Supabase. Se aparecer PGRST205/schema cache, faça Reboot app no Streamlit e aguarde alguns segundos.")

            if not loja_minis_admin:
                st.info("Nenhuma mini cadastrada na loja ainda.")
            else:
                loja_opcoes = {f"#{m.get('id')} - {m.get('nome','')} — {m.get('status','disponivel')}": m for m in loja_minis_admin}
                loja_escolha = st.selectbox("Editar item da loja", list(loja_opcoes.keys()), key="loja_editar_select")
                loja_edit = loja_opcoes[loja_escolha]

                with st.expander("Abrir edição do item da loja", expanded=False):
                    with st.form(f"form_loja_editar_{loja_edit['id']}"):
                        el1, el2 = st.columns(2)
                        with el1:
                            el_nome = st.text_input("Nome", value=loja_edit.get("nome") or "", key=f"el_nome_{loja_edit['id']}")
                            el_marca = st.text_input("Marca", value=loja_edit.get("marca") or "", key=f"el_marca_{loja_edit['id']}")
                            el_serie = st.text_input("Série", value=loja_edit.get("serie") or "", key=f"el_serie_{loja_edit['id']}")
                            el_ano = st.text_input("Ano", value=loja_edit.get("ano") or "", key=f"el_ano_{loja_edit['id']}")
                            el_foto = st.file_uploader("Trocar foto", type=["jpg", "jpeg", "png"], key=f"el_foto_{loja_edit['id']}")
                        with el2:
                            categoria_atual = obter_categoria_loja_item(loja_edit)
                            el_categoria = st.selectbox("Categoria da loja", CATEGORIAS_LOJA, index=CATEGORIAS_LOJA.index(categoria_atual) if categoria_atual in CATEGORIAS_LOJA else len(CATEGORIAS_LOJA)-1, key=f"el_categoria_{loja_edit['id']}")
                            op_r = ["Comum", "TH", "STH", "Premium", "RLC", "Chase", "Especial"]
                            r_atual = loja_edit.get("raridade") or "Comum"
                            el_raridade = st.selectbox("Raridade", op_r, index=op_r.index(r_atual) if r_atual in op_r else 0, key=f"el_rar_{loja_edit['id']}")
                            el_valor = st.number_input("Preço de venda", min_value=0.0, step=1.0, value=float(loja_edit.get("valor") or 0), key=f"el_valor_{loja_edit['id']}")
                            el_estimado = st.number_input("Valor estimado", min_value=0.0, step=1.0, value=float(loja_edit.get("valor_estimado") or 0), key=f"el_estimado_{loja_edit['id']}")
                            el_estoque = st.number_input("Disponíveis em estoque", min_value=0, step=1, value=int(obter_estoque_loja_item(loja_edit)), key=f"el_estoque_{loja_edit['id']}")
                            op_st = ["disponivel", "reservado", "vendido"]
                            st_atual = loja_edit.get("status") or "disponivel"
                            el_status = st.selectbox("Status", op_st, index=op_st.index(st_atual) if st_atual in op_st else 0, key=f"el_status_{loja_edit['id']}")
                            el_destaque = st.text_input("Destaque", value=limpar_metadados_destaque_loja(loja_edit.get("destaque") or ""), key=f"el_dest_{loja_edit['id']}")

                        sl1, sl2 = st.columns(2)
                        with sl1:
                            salvar_loja = st.form_submit_button("Salvar item da loja")
                        with sl2:
                            excluir_loja_btn = st.form_submit_button("Excluir item da loja")

                        if salvar_loja:
                            nova_foto = loja_edit.get("foto_url") or ""
                            if el_foto is not None:
                                nova_foto = upload_storage_loja(el_foto, el_nome)
                            status_final = "vendido" if int(el_estoque or 0) <= 0 else "disponivel"
                            atualizar_loja_mini(loja_edit["id"], {
                                "nome": el_nome,
                                "marca": el_marca,
                                "serie": el_serie,
                                "ano": el_ano,
                                "raridade": el_raridade,
                                "valor": el_valor,
                                "valor_estimado": el_estimado,
                                "foto_url": nova_foto,
                                "status": status_final,
                                "destaque": atualizar_destaque_com_qtd_e_categoria(el_destaque, el_estoque, el_categoria),
                            })
                            st.success("Item da loja atualizado.")
                            st.rerun()

                        if excluir_loja_btn:
                            excluir_loja_mini(loja_edit["id"])
                            st.success("Item removido da loja.")
                            st.rerun()

                st.divider()
                st.markdown("### 🧩 Categorias da loja")
                abas_categoria_admin = st.tabs(CATEGORIAS_LOJA)
                for aba_cat_admin, categoria_admin in zip(abas_categoria_admin, CATEGORIAS_LOJA):
                    with aba_cat_admin:
                        itens_categoria_admin = [m for m in loja_minis_admin if obter_categoria_loja_item(m) == categoria_admin]
                        if not itens_categoria_admin:
                            st.info(f"Nenhuma mini na categoria {categoria_admin}.")
                            continue

                        for item in itens_categoria_admin:
                            foto_admin = get_foto_item(item)
                            img_admin = imagem_html(foto_admin, "market-img") if foto_admin else '<div class="market-empty">🏎️</div>'
                            nome_admin = html.escape(str(item.get('nome') or 'Mini'))
                            marca_admin = html.escape(str(item.get('marca') or 'Hot Wheels'))
                            serie_admin = html.escape(str(item.get('serie') or ''))
                            raridade_admin = html.escape(str(item.get('raridade') or 'Comum'))
                            categoria_admin_safe = html.escape(obter_categoria_loja_item(item))
                            estoque_admin = obter_estoque_loja_item(item)
                            status_admin = "ESGOTADO" if estoque_admin <= 0 else "DISPONÍVEL"
                            status_admin_classe = "market-tag-sold" if estoque_admin <= 0 else "market-tag-ok"
                            estoque_admin_texto = texto_unidades_estoque(estoque_admin)

                            st.markdown(f"""
                            <div class="market-card">
                                {img_admin}
                                <div class="market-body">
                                    <div class="favorite-chip">🏁</div>
                                    <h3 class="market-name">{nome_admin}</h3>
                                    <div class="market-tags">
                                        <span class="market-tag market-tag-gold">{categoria_admin_safe}</span>
                                        <span class="market-tag market-tag-gold">{raridade_admin}</span>
                                        <span class="market-tag {status_admin_classe}">{status_admin}</span>
                                    </div>
                                    <p class="market-line"><b>Marca:</b> {marca_admin}</p>
                                    <p class="market-line"><b>Série:</b> {serie_admin}</p>
                                    <div class="market-price-grid">
                                        <div class="market-price"><small>Preço</small><strong>{money(item.get('valor') or 0)}</strong></div>
                                        <div class="market-price"><small>Estimado</small><strong>{money(item.get('valor_estimado') or 0)}</strong></div>
                                        <div class="market-price"><small>Disponíveis</small><strong>{estoque_admin_texto}</strong></div>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

        # =========================
        # ABA PRÉ-VENDA
        # =========================
        with aba_pre_venda_admin:
            render_pre_vendas_admin(clientes)

        # =========================
        # ABA PEDIDOS
        # =========================
        with aba_pedidos:
            st.markdown("""
            <div class="admin-work-card">
                <h3>💰 Pedidos da loja e lançamentos</h3>
                <p>Gerencie solicitações da Loja. Ao clicar em Pago + garagem, o sistema conclui o pedido, lança a mini na garagem do cliente e atualiza o estoque automaticamente.</p>
            </div>
            """, unsafe_allow_html=True)

            try:
                pedidos = buscar_pedidos()
            except Exception:
                pedidos = []
                st.error("Tabela pedidos ainda não existe. Rode o SQL de pedidos no Supabase.")

            clientes_por_id = {c.get("id"): c for c in clientes}
            loja_por_id = {}
            try:
                for item_loja in buscar_loja_minis(apenas_disponiveis=False):
                    loja_por_id[item_loja.get("id")] = item_loja
            except Exception:
                loja_por_id = {}

            st.subheader("Pedidos recebidos pela Loja")

            if not pedidos:
                st.info("Ainda não há pedidos/reservas feitos pelos clientes.")
            else:
                for ped in pedidos:
                    cliente_ped = clientes_por_id.get(ped.get("usuario_id"), {})
                    loja_item = loja_por_id.get(ped.get("loja_mini_id"), {})
                    status_ped = ped.get("status") or "solicitado"

                    st.markdown(f"""
                    <div class="user-card">
                        <div class="user-head">
                            <div>
                                <div class="user-name">#{ped.get('id')} — {html.escape(str(ped.get('nome') or loja_item.get('nome') or 'Mini'))}</div>
                                <div class="user-email">Cliente: {html.escape(str(cliente_ped.get('nome', 'Cliente')))} — {html.escape(str(cliente_ped.get('email', '-')))}</div>
                            </div>
                            <div>
                                <span class="badge-status badge-pedido-{html.escape(str(status_ped))}">{html.escape(str(status_ped))}</span>
                                <span class="badge-raridade badge-{html.escape(str(ped.get('raridade') or loja_item.get('raridade') or 'Comum'))}">{html.escape(str(ped.get('raridade') or loja_item.get('raridade') or 'Comum'))}</span>
                            </div>
                        </div>
                        <div class="user-info-grid">
                            <div class="user-info-item"><small>Valor</small><strong>{money(ped.get('valor') or loja_item.get('valor') or 0)}</strong></div>
                            <div class="user-info-item"><small>Loja ID</small><strong>{html.escape(str(ped.get('loja_mini_id') or '-'))}</strong></div>
                            <div class="user-info-item"><small>Observação</small><strong>{html.escape(str(ped.get('observacoes') or '-'))}</strong></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if status_ped == "aguardando_pix":
                        st.markdown(pix_card_html(ped, "Pix aguardando confirmação"), unsafe_allow_html=True)

                    b1, b2, b3, b4, b5, b6 = st.columns([1, 1, 1, 1.4, 1.7, 2.2])
                    with b1:
                        if st.button("🟡 Pendente", key=f"ped_pendente_{ped['id']}", disabled=status_ped == "concluido"):
                            atualizar_pedido(ped["id"], {"status": "pendente"})
                            st.rerun()
                    with b2:
                        if st.button("🔵 Reservar", key=f"ped_reservar_{ped['id']}", disabled=status_ped == "concluido"):
                            atualizar_pedido(ped["id"], {"status": "reservado"})
                            if ped.get("loja_mini_id"):
                                try:
                                    atualizar_loja_mini(ped.get("loja_mini_id"), {"status": "reservado"})
                                except Exception:
                                    pass
                            st.rerun()
                    with b3:
                        if st.button("🔴 Cancelar", key=f"ped_cancelar_{ped['id']}", disabled=status_ped == "concluido"):
                            atualizar_pedido(ped["id"], {"status": "cancelado"})
                            if ped.get("loja_mini_id"):
                                try:
                                    atualizar_loja_mini(ped.get("loja_mini_id"), {"status": "disponivel"})
                                except Exception:
                                    pass
                            st.rerun()
                    with b4:
                        if st.button("💳 Pix", key=f"ped_pix_{ped['id']}", disabled=status_ped in ["concluido", "cancelado"]):
                            atualizar_pedido(ped["id"], {"status": "aguardando_pix", "observacoes": f"Pix gerado para conferência manual. {gerar_pix_copia_cola(ped)}"})
                            st.rerun()
                    with b5:
                        if st.button("🟢 Confirmar Pix + garagem", key=f"ped_pix_confirmar_{ped['id']}", disabled=status_ped == "concluido"):
                            ok, msg = concluir_pedido_na_garagem(ped, loja_item)
                            if ok:
                                st.success(msg)
                            else:
                                st.warning(msg)
                            st.rerun()
                    with b6:
                        if status_ped == "concluido":
                            st.success("Pedido concluído e mini já lançada.")
                        else:
                            st.caption("Pix assistido: cliente paga, admin confirma e lança na garagem.")

            st.divider()
            st.subheader("Lançamento manual direto")

            if not clientes:
                st.warning("Nenhum cliente cadastrado ainda. Crie um cliente na aba Clientes para conseguir lançar minis.")
            else:
                mapa_clientes = {f"{c.get('nome','')} — {c.get('email','')}": c for c in clientes}
                with st.expander("Lançar mini manualmente sem passar pela loja", expanded=False):
                    with st.form("form_admin_lancar_mini"):
                        cliente_label = st.selectbox("Cliente", list(mapa_clientes.keys()), key="adm_lancar_cliente")
                        cliente_sel = mapa_clientes[cliente_label]

                        a1, a2 = st.columns(2)
                        with a1:
                            nome_mini = st.text_input("Nome da mini", key="adm_mini_nome")
                            marca_mini = st.text_input("Marca", value="Hot Wheels", key="adm_mini_marca")
                            serie_mini = st.text_input("Série", key="adm_mini_serie")
                            ano_mini = st.text_input("Ano", key="adm_mini_ano")
                            foto_mini_adm = st.file_uploader("Foto da mini", type=["jpg", "jpeg", "png"], key="adm_mini_foto")
                        with a2:
                            raridade_mini = st.selectbox("Raridade", ["Comum", "TH", "STH", "Premium", "RLC", "Chase", "Especial"], key="adm_mini_raridade")
                            valor_pago_mini = st.number_input("Valor pago", min_value=0.0, step=1.0, key="adm_mini_valor_pago")
                            valor_estimado_mini = st.number_input("Valor estimado", min_value=0.0, step=1.0, key="adm_mini_valor_estimado")
                            status_pagamento = st.selectbox("Status pagamento", ["pendente", "pago", "reservado", "pre_datado", "cancelado"], key="adm_status_pagamento")
                            data_pagamento_prevista = None
                            if status_pagamento in ["pendente", "reservado", "pre_datado"]:
                                data_pagamento_prevista = st.date_input("Data prevista de pagamento (opcional)", value=None, format="DD/MM/YYYY", key="adm_data_pagamento_prevista")
                            tipo_mini = st.selectbox("Tipo", ["compra", "presente", "premio", "vip"], key="adm_tipo_mini")
                            destaque_cliente = st.selectbox("Destaque", ["", "Top comprador", "Top ganhador", "Cliente VIP"], key="adm_destaque_cliente")

                        salvar_lancamento = st.form_submit_button("Lançar mini na garagem do cliente")
                        if salvar_lancamento:
                            if not nome_mini:
                                st.error("Informe o nome da mini.")
                            else:
                                foto_url = upload_storage(foto_mini_adm, "minis", f"{cliente_sel.get('id')}_{nome_mini}")
                                cadastrar_mini(
                                    cliente_sel["id"], nome_mini, marca_mini, serie_mini, ano_mini, raridade_mini,
                                    valor_pago_mini, valor_estimado_mini, foto_url,
                                    status_pagamento, tipo_mini, destaque_cliente, data_pagamento_prevista
                                )
                                st.success("Mini lançada na garagem do cliente.")
                                st.rerun()

            st.divider()
            st.subheader("Últimos lançamentos na garagem")

            if not todas_minis:
                st.info("Ainda não há lançamentos.")
            else:
                clientes_por_id = {c.get("id"): c for c in clientes}
                for mini in todas_minis[:12]:
                    dono = clientes_por_id.get(mini.get("usuario_id"), {})
                    st.markdown(f"""
                    <div class="user-card">
                        <div class="user-head">
                            <div>
                                <div class="user-name">{html.escape(str(mini.get('nome', '')))}</div>
                                <div class="user-email">Cliente: {html.escape(str(dono.get('nome', 'sem cliente')))} — {html.escape(str(dono.get('email', '-')))}</div>
                            </div>
                            <div>
                                <span class="badge-status badge-status-{html.escape(str(mini.get('status_pagamento') or 'pendente'))}">{html.escape(str(mini.get('status_pagamento') or 'pendente'))}</span>
                                <span class="badge-tipo">{html.escape(str(mini.get('tipo_mini') or 'compra'))}</span>
                            </div>
                        </div>
                        <div class="user-info-grid">
                            <div class="user-info-item"><small>Valor pago</small><strong>{money(mini.get('valor_pago') or 0)}</strong></div>
                            <div class="user-info-item"><small>Estimado</small><strong>{money(mini.get('valor_estimado') or 0)}</strong></div>
                            <div class="user-info-item"><small>Destaque</small><strong>{html.escape(str(mini.get('destaque_cliente') or '-'))}</strong></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # =========================
        # ABA MINIS
        # =========================
        with aba_minis:
            st.markdown("""
            <div class="admin-work-card">
                <h3>✏️ Editar mini de qualquer cliente</h3>
                <p>Altere dono, dados, status de pagamento, tipo, destaque ou exclua a mini.</p>
            </div>
            """, unsafe_allow_html=True)

            if not todas_minis:
                st.info("Ainda não há minis cadastradas para edição administrativa.")
            elif not clientes:
                st.info("Há minis, mas ainda não há clientes suficientes para transferência/edição completa.")
            else:
                mapa_clientes = {f"{c.get('nome','')} — {c.get('email','')}": c for c in clientes}
                clientes_por_id = {c.get("id"): c for c in clientes}
                opcoes_minis = {}

                for m in todas_minis:
                    dono = clientes_por_id.get(m.get("usuario_id"), {})
                    label = f"#{m.get('id')} - {m.get('nome','')} — {dono.get('nome','sem cliente')}"
                    opcoes_minis[label] = m

                escolha_mini = st.selectbox("Mini para editar", list(opcoes_minis.keys()), key="adm_select_mini_editar")
                mini_edit = opcoes_minis[escolha_mini]

                with st.expander("Abrir edição administrativa", expanded=True):
                    with st.form(f"form_admin_editar_mini_{mini_edit['id']}"):
                        labels_clientes = list(mapa_clientes.keys())
                        cliente_atual_index = 0

                        for i, label in enumerate(labels_clientes):
                            if mapa_clientes[label].get("id") == mini_edit.get("usuario_id"):
                                cliente_atual_index = i
                                break

                        novo_dono_label = st.selectbox("Dono da mini", labels_clientes, index=cliente_atual_index, key=f"adm_novo_dono_{mini_edit['id']}")
                        novo_dono = mapa_clientes[novo_dono_label]

                        e1, e2 = st.columns(2)
                        with e1:
                            e_nome = st.text_input("Nome", value=mini_edit.get("nome") or "", key=f"adm_e_nome_{mini_edit['id']}")
                            e_marca = st.text_input("Marca", value=mini_edit.get("marca") or "", key=f"adm_e_marca_{mini_edit['id']}")
                            e_serie = st.text_input("Série", value=mini_edit.get("serie") or "", key=f"adm_e_serie_{mini_edit['id']}")
                            e_ano = st.text_input("Ano", value=mini_edit.get("ano") or "", key=f"adm_e_ano_{mini_edit['id']}")
                            e_foto = st.file_uploader("Trocar foto", type=["jpg", "jpeg", "png"], key=f"adm_e_foto_{mini_edit['id']}")
                        with e2:
                            opcoes_r = ["Comum", "TH", "STH", "Premium", "RLC", "Chase", "Especial"]
                            idx_r = opcoes_r.index(mini_edit.get("raridade")) if mini_edit.get("raridade") in opcoes_r else 0
                            e_raridade = st.selectbox("Raridade", opcoes_r, index=idx_r, key=f"adm_e_raridade_{mini_edit['id']}")
                            e_valor_pago = st.number_input("Valor pago", min_value=0.0, step=1.0, value=float(mini_edit.get("valor_pago") or 0), key=f"adm_e_valor_pago_{mini_edit['id']}")
                            e_valor_estimado = st.number_input("Valor estimado", min_value=0.0, step=1.0, value=float(mini_edit.get("valor_estimado") or 0), key=f"adm_e_valor_estimado_{mini_edit['id']}")

                            sts = ["pendente", "pago", "reservado", "cancelado"]
                            atual_st = mini_edit.get("status_pagamento") or "pendente"
                            e_status = st.selectbox("Status pagamento", sts, index=sts.index(atual_st) if atual_st in sts else 0, key=f"adm_e_status_{mini_edit['id']}")
                            e_data_pagamento = st.date_input(
                                "Data prevista de pagamento (opcional)",
                                value=normalizar_data_pagamento_prevista(mini_edit.get("data_pagamento_prevista")),
                                format="DD/MM/YYYY",
                                key=f"adm_e_data_pagamento_{mini_edit['id']}"
                            )

                            tipos = ["compra", "presente", "premio", "vip"]
                            atual_tipo = mini_edit.get("tipo_mini") or "compra"
                            e_tipo = st.selectbox("Tipo", tipos, index=tipos.index(atual_tipo) if atual_tipo in tipos else 0, key=f"adm_e_tipo_{mini_edit['id']}")

                            destaques = ["", "Top comprador", "Top ganhador", "Cliente VIP"]
                            atual_dest = mini_edit.get("destaque_cliente") or ""
                            e_destaque = st.selectbox("Destaque", destaques, index=destaques.index(atual_dest) if atual_dest in destaques else 0, key=f"adm_e_destaque_{mini_edit['id']}")

                        s1, s2 = st.columns(2)
                        with s1:
                            salvar_admin = st.form_submit_button("Salvar alterações")
                        with s2:
                            excluir_admin = st.form_submit_button("Excluir mini")

                        if salvar_admin:
                            nova_foto = mini_edit.get("foto_url") or ""
                            if e_foto is not None:
                                nova_foto = upload_storage(e_foto, "minis", f"{novo_dono.get('id')}_{e_nome}")

                            dados = {
                                "usuario_id": novo_dono.get("id"),
                                "nome": e_nome,
                                "marca": e_marca,
                                "serie": e_serie,
                                "ano": e_ano,
                                "raridade": e_raridade,
                                "valor_pago": e_valor_pago,
                                "valor_estimado": e_valor_estimado,
                                "foto_url": nova_foto,
                                "status_pagamento": e_status,
                                "tipo_mini": e_tipo,
                                "destaque_cliente": e_destaque,
                                "data_pagamento_prevista": str(e_data_pagamento) if e_data_pagamento else None,
                            }

                            try:
                                atualizar_mini(mini_edit["id"], dados)
                            except Exception:
                                dados.pop("status_pagamento", None)
                                dados.pop("tipo_mini", None)
                                dados.pop("destaque_cliente", None)
                                dados.pop("data_pagamento_prevista", None)
                                atualizar_mini(mini_edit["id"], dados)

                            st.success("Mini atualizada com sucesso.")
                            st.rerun()

                        if excluir_admin:
                            excluir_mini(mini_edit["id"])
                            st.success("Mini excluída com sucesso.")
                            st.rerun()

        # =========================
        # ABA FINANCEIRO
        # =========================
        with aba_financeiro:
            st.markdown("""
            <div class="admin-work-card">
                <h3>📊 Financeiro e ranking</h3>
                <p>Resumo de valores pagos, pendentes, reservas e ranking dos compradores.</p>
            </div>
            """, unsafe_allow_html=True)

            f1, f2, f3, f4 = st.columns(4)
            with f1:
                st.markdown(f'<div class="metric-card"><div class="metric-icon">🟢</div><h2>{money(total_pago_fin)}</h2><p>Pago</p></div>', unsafe_allow_html=True)
            with f2:
                st.markdown(f'<div class="metric-card"><div class="metric-icon">🟡</div><h2>{money(total_pendente_fin)}</h2><p>Pendente</p></div>', unsafe_allow_html=True)
            with f3:
                st.markdown(f'<div class="metric-card"><div class="metric-icon">🔵</div><h2>{money(total_reservado_fin)}</h2><p>Reservado</p></div>', unsafe_allow_html=True)
            with f4:
                st.markdown(f'<div class="metric-card"><div class="metric-icon">🏎️</div><h2>{len(todas_minis)}</h2><p>Minis lançadas</p></div>', unsafe_allow_html=True)

            st.subheader("Top compradores")

            ranking = {}
            clientes_por_id = {c.get("id"): c for c in clientes}
            for mini in todas_minis:
                if (mini.get("status_pagamento") or "pendente") == "pago":
                    uid = mini.get("usuario_id")
                    ranking.setdefault(uid, {"valor": 0.0, "qtd": 0})
                    ranking[uid]["valor"] += float(mini.get("valor_pago") or 0)
                    ranking[uid]["qtd"] += 1

            ranking_ordenado = sorted(ranking.items(), key=lambda item: item[1]["valor"], reverse=True)

            if not ranking_ordenado:
                st.info("Ainda não há compras pagas para montar ranking.")
            else:
                for pos, (uid, dados_rank) in enumerate(ranking_ordenado[:10], start=1):
                    cli = clientes_por_id.get(uid, {})
                    st.markdown(f"""
                    <div class="user-card">
                        <div class="user-head">
                            <div>
                                <div class="user-name">#{pos} — {html.escape(str(cli.get('nome', 'Cliente')))}</div>
                                <div class="user-email">{html.escape(str(cli.get('email', '-')))}</div>
                            </div>
                            <div>
                                <span class="badge-destaque">Top comprador</span>
                            </div>
                        </div>
                        <div class="user-info-grid">
                            <div class="user-info-item"><small>Total pago</small><strong>{money(dados_rank['valor'])}</strong></div>
                            <div class="user-info-item"><small>Minis pagas</small><strong>{dados_rank['qtd']}</strong></div>
                            <div class="user-info-item"><small>Status</small><strong>ATIVO</strong></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)



        # =========================
        # ABA HALL DA FAMA ADMIN
        # =========================
        with aba_hall_admin:
            st.markdown("""
            <div class="admin-work-card">
                <h3>🏆 Hall da Fama GarageHub</h3>
                <p>Destaque automático das minis mais especiais: RLC, STH, Chase, VIP, presentes e maiores valores.</p>
            </div>
            """, unsafe_allow_html=True)

            hall_minis = [m for m in todas_minis if (m.get("raridade") in ["RLC", "STH", "Chase"] or (m.get("tipo_mini") in ["presente", "premio", "vip"]) or float(m.get("valor_estimado") or 0) >= 100)]
            hall_minis = sorted(hall_minis, key=lambda m: float(m.get("valor_estimado") or 0), reverse=True)

            if not hall_minis:
                st.info("Ainda não há minis elegíveis para o Hall da Fama.")
            else:
                cards = []
                clientes_por_id = {c.get("id"): c for c in clientes}
                for mini in hall_minis[:12]:
                    dono = clientes_por_id.get(mini.get("usuario_id"), {})
                    raridade = html.escape(str(mini.get("raridade") or "Comum"))
                    cards.append(
                        f'<div class="mini-card hall-glow">'
                        f'{imagem_html(get_foto_item(mini))}'
                        f'<div class="mini-body">'
                        f'<h3 class="mini-title">🏆 {html.escape(str(mini.get("nome") or "Mini"))}</h3>'
                        f'<span class="badge-raridade badge-{raridade}">{raridade}</span>'
                        f'<span class="badge-destaque">{html.escape(str(mini.get("tipo_mini") or "Destaque"))}</span>'
                        f'<p class="mini-meta"><b>Dono:</b> {html.escape(str(dono.get("nome") or "Cliente"))}</p>'
                        f'<p class="mini-meta"><b>Série:</b> {html.escape(str(mini.get("serie") or "-"))}</p>'
                        f'<div class="price-box"><small>Valor estimado</small><strong>{money(mini.get("valor_estimado") or 0)}</strong></div>'
                        f'</div></div>'
                    )
                st.markdown('<div class="garage-grid">' + ''.join(cards) + '</div>', unsafe_allow_html=True)

            st.divider()
            render_gamificacao_admin(clientes, todas_minis)

        # =========================
        # ABA RANKING ADMIN
        # =========================
        with aba_ranking_admin:
            st.markdown("""
            <div class="admin-work-card">
                <h3>👑 Ranking e Gamificação GarageHub</h3>
                <p>Pontuação geral dos clientes com compras, coleção, raridades, cotas de rifas, vitórias, níveis e conquistas.</p>
            </div>
            """, unsafe_allow_html=True)

            render_gamificacao_admin(clientes, todas_minis)


        # =========================
        # ABA TIMELINE ADMIN
        # =========================
        with aba_timeline_admin:
            st.markdown("""
            <div class="admin-work-card">
                <h3>🕒 Timeline da comunidade</h3>
                <p>Movimentos recentes de pedidos, vendas e minis lançadas na garagem.</p>
            </div>
            """, unsafe_allow_html=True)

            try:
                pedidos_timeline = buscar_pedidos()[:10]
            except Exception:
                pedidos_timeline = []

            clientes_por_id = {c.get("id"): c for c in clientes}
            eventos = []
            for ped in pedidos_timeline:
                cli = clientes_por_id.get(ped.get("usuario_id"), {})
                eventos.append(f"<div class='timeline-item'>📦 Pedido <strong>#{ped.get('id')}</strong> — {html.escape(str(ped.get('nome') or 'Mini'))} para {html.escape(str(cli.get('nome') or 'Cliente'))}. Status: <strong>{html.escape(str(ped.get('status') or 'solicitado'))}</strong></div>")
            for mini in todas_minis[:10]:
                cli = clientes_por_id.get(mini.get("usuario_id"), {})
                eventos.append(f"<div class='timeline-item'>🏎️ Mini <strong>{html.escape(str(mini.get('nome') or 'Mini'))}</strong> lançada na garagem de {html.escape(str(cli.get('nome') or 'Cliente'))}. Status: <strong>{html.escape(str(mini.get('status_pagamento') or 'pendente'))}</strong></div>")

            if eventos:
                st.markdown("".join(eventos[:16]), unsafe_allow_html=True)
            else:
                st.info("Sem eventos recentes ainda.")

        # =========================
        # ABA SORTEIOS ADMIN
        # =========================
        with aba_sorteios_admin:
            render_rifas_admin(clientes)

        # =========================
        # ABA LAB ADMIN
        # =========================
        with aba_lab_admin:
            st.markdown("""
            <div class="admin-work-card">
                <h3>🧪 Lab IA, Pix e automações</h3>
                <p>Área segura para próximas integrações: scanner IA, Mercado Pago/Pix, notificações e app mobile.</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div class="feature-grid">
                <div class="lab-card"><h3>📱 Scanner IA</h3><p>Agora com captura, sugestão editável e ações de admin.</p></div>
                <div class="lab-card"><h3>💳 Pix / Mercado Pago</h3><p>Preparado para gerar cobrança e confirmar pagamento automaticamente.</p></div>
                <div class="lab-card"><h3>🔔 Notificações</h3><p>Preparado para avisar cliente sobre pedido, pagamento e lançamento na garagem.</p></div>
            </div>
            """, unsafe_allow_html=True)
            render_scanner_ia_demo()
            st.warning("Integrações reais precisam das chaves/API do provedor escolhido. O scanner acima já funciona em modo assistido/local e está pronto para conectar IA depois.")

        # =========================
        # ABA EXECUTIVO ADMIN
        # =========================
        with aba_exec_admin:
            try:
                pedidos_exec = buscar_pedidos()
            except Exception:
                pedidos_exec = []
            render_admin_executivo(clientes, todas_minis, pedidos_exec)
            render_hall_automatico(clientes, todas_minis)
            render_gamificacao_admin(clientes, todas_minis)

        # =========================
        # ABA CHECKOUT ADMIN
        # =========================
        with aba_checkout_admin:
            try:
                pedidos_checkout = buscar_pedidos()
            except Exception:
                pedidos_checkout = []
            st.markdown('<div class="admin-work-card"><h3>💳 Checkout e Pix</h3><p>Admin acompanha pagamentos, Pix assistido e estrutura preparada para gateway real.</p></div>', unsafe_allow_html=True)
            render_checkout_real_visual([p for p in pedidos_checkout if (p.get("status") or "") in ["solicitado", "pendente", "reservado", "aguardando_pix", "pago"]])

        # =========================
        # ABA NOTIFICAÇÕES ADMIN
        # =========================
        with aba_notif_admin:
            try:
                pedidos_notif = buscar_pedidos()
            except Exception:
                pedidos_notif = []
            render_notificacoes_demo(usuario, pedidos_notif)
            render_timeline_pedidos(pedidos_notif, {c.get("id"): c for c in clientes})


    # =========================
    # USUÁRIO NORMAL
    # =========================
    else:
        instagram = usuario.get("instagram", "") or ""
        if instagram and not instagram.startswith("@"):
            instagram = f"@{instagram}"

        st.markdown(f"""
        <div class="member-card">
            <div class="member-top">
                <div>
                    <h1>🏁 GarageHub</h1>
                    <p class="member-sub">Comunidade Garagem Hot Wheels</p>
                </div>
                <div>{perfil_html(get_foto_perfil_usuario(usuario), usuario.get('nome', ''))}</div>
            </div>
            <div class="member-info">
                <p><span>Nome:</span> {html.escape(str(usuario.get('nome', '')))}</p>
                <p><span>Status:</span> {html.escape(str(usuario.get('status', '')))}</p>
                <p><span>Cidade:</span> {html.escape(str(usuario.get('cidade', '')))} / {html.escape(str(usuario.get('estado', '')))}</p>
                <p><span>Instagram:</span> {html.escape(instagram)}</p>
                <p><span>Telefone:</span> {html.escape(str(usuario.get('telefone', '')))}</p>
                <p><span>Plano:</span> {"Membro VIP" if (usuario.get("nivel_cliente") or "comum") == "vip" else "Cliente comum"}</p>
            </div>
            <div class="member-footer">
                <div class="member-code">{html.escape(str(usuario.get('codigo_membro', '')))}</div>
                <div class="member-badge">{"MEMBRO VIP" if (usuario.get("nivel_cliente") or "comum") == "vip" else "CLIENTE COMUM"}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        aba_garagem, aba_loja_cliente, aba_pre_venda_cliente, aba_rifas_cliente, aba_meus_pedidos, aba_hall_cliente, aba_ranking_cliente, aba_carteirinha_qr, aba_lab_cliente, aba_pagamentos_cliente, aba_perfil_cliente, aba_mobile_cliente, aba_notif_cliente, aba_scanner_cliente = st.tabs([
            "🏎️ Minha garagem",
            "🛒 Loja",
            "🚧 Pré-venda",
            "🎟️ Rifas",
            "📦 Meus pedidos",
            "🏆 Hall da Fama",
            "👑 Ranking",
            "🎫 Carteirinha QR",
            "🧪 Lab IA/Pix",
            "💳 Pagamentos",
            "👤 Perfil",
            "📱 Mobile",
            "🔔 Notificações",
            "🤖 Scanner IA"
        ])

        with aba_loja_cliente:
            st.markdown("""
            <div class="market-hero">
                <div class="market-kicker">🏁 Marketplace GarageHub</div>
                <h1 class="market-title">Loja premium de minis</h1>
                <p class="market-desc">Vitrine exclusiva para colecionadores: raridades, destaques, reservas e compras acompanhadas pelo admin até entrar na sua garagem oficial.</p>
                <div class="market-stats">
                    <div class="market-stat"><strong>VIP</strong><small>acesso especial</small></div>
                    <div class="market-stat"><strong>1:64</strong><small>colecionáveis</small></div>
                    <div class="market-stat"><strong>GHW</strong><small>garagem oficial</small></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            try:
                loja_disponiveis = [
                    item for item in buscar_loja_minis(apenas_disponiveis=True)
                    if obter_estoque_loja_item(item) > 0
                ]
            except Exception as e:
                loja_disponiveis = []
                st.error(f"Não consegui carregar a loja agora. Erro real: {e}")

            if not loja_disponiveis:
                st.info("Nenhuma mini disponível na loja agora.")
            else:
                st.markdown('<div class="market-filter-box">', unsafe_allow_html=True)
                f1, f2, f3, f4 = st.columns([2, 1.1, 1, 1])
                with f1:
                    busca_loja = st.text_input("🔎 Buscar por nome, marca ou série", key="busca_loja_cliente", placeholder="Ex: Skyline, RLC, Gulf...")
                with f2:
                    categorias_loja_cliente = ["Todas"] + CATEGORIAS_LOJA
                    filtro_categoria_loja = st.selectbox("Categoria", categorias_loja_cliente, key="filtro_categoria_loja")
                with f3:
                    raridades_loja = ["Todas"] + sorted(list(set([str(m.get("raridade") or "Comum") for m in loja_disponiveis])))
                    filtro_raridade_loja = st.selectbox("Raridade", raridades_loja, key="filtro_raridade_loja")
                with f4:
                    ordem_loja = st.selectbox("Ordenar", ["Novidades", "Menor preço", "Maior preço", "Nome A-Z"], key="ordem_loja")
                st.markdown('</div>', unsafe_allow_html=True)

                itens_loja = loja_disponiveis[:]
                if busca_loja:
                    b = busca_loja.lower().strip()
                    itens_loja = [m for m in itens_loja if b in str(m.get("nome", "")).lower() or b in str(m.get("marca", "")).lower() or b in str(m.get("serie", "")).lower()]
                if filtro_categoria_loja != "Todas":
                    itens_loja = [m for m in itens_loja if obter_categoria_loja_item(m) == filtro_categoria_loja]
                if filtro_raridade_loja != "Todas":
                    itens_loja = [m for m in itens_loja if str(m.get("raridade") or "Comum") == filtro_raridade_loja]

                if ordem_loja == "Menor preço":
                    itens_loja = sorted(itens_loja, key=lambda m: float(m.get("valor") or 0))
                elif ordem_loja == "Maior preço":
                    itens_loja = sorted(itens_loja, key=lambda m: float(m.get("valor") or 0), reverse=True)
                elif ordem_loja == "Nome A-Z":
                    itens_loja = sorted(itens_loja, key=lambda m: str(m.get("nome") or ""))

                st.caption(f"🛒 Exibindo {len(itens_loja)} mini(s) disponíveis na vitrine premium.")

                if not itens_loja:
                    st.warning("Nenhuma mini encontrada com esses filtros.")
                else:
                    destaque = itens_loja[0]
                    st.markdown(f"""
                    <div class="store-callout">
                        <h3>🔥 Destaque da vitrine: {html.escape(str(destaque.get('nome') or 'Mini especial'))}</h3>
                        <p>{html.escape(str(destaque.get('marca') or 'Hot Wheels'))} • {html.escape(str(destaque.get('serie') or ''))} • {money(destaque.get('valor') or 0)}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    for i in range(0, len(itens_loja), 2):
                        cols = st.columns(2)
                        for col, item in zip(cols, itens_loja[i:i+2]):
                            with col:
                                foto_item = get_foto_item(item)
                                img = imagem_html(foto_item, "market-img") if foto_item else '<div class="market-empty">🏎️</div>'
                                nome_item = html.escape(str(item.get("nome") or "Mini"))
                                marca_item = html.escape(str(item.get("marca") or "Hot Wheels"))
                                serie_item = html.escape(str(item.get("serie") or ""))
                                ano_item = html.escape(str(item.get("ano") or ""))
                                raridade_item = html.escape(str(item.get("raridade") or "Comum"))
                                categoria_item = html.escape(obter_categoria_loja_item(item))
                                estoque_item = obter_estoque_loja_item(item)
                                estoque_item_texto = html.escape(texto_unidades_estoque(estoque_item))
                                estoque_item_badge = badge_estoque_loja(estoque_item)
                                tag_raro = "market-tag-rare" if raridade_item in ["RLC", "STH", "Chase", "Especial"] else "market-tag-gold"

                                st.markdown(f"""
                                <div class="market-card">
                                    {img}
                                    <div class="market-body">
                                        <div class="favorite-chip">❤️</div>
                                        <h3 class="market-name">{nome_item}</h3>
                                        <div class="market-tags">
                                            <span class="market-tag market-tag-gold">{categoria_item}</span>
                                            <span class="market-tag {tag_raro}">{raridade_item}</span>
                                            {estoque_item_badge}
                                        </div>
                                        <p class="market-line"><b>Marca:</b> {marca_item}</p>
                                        <p class="market-line"><b>Série:</b> {serie_item}</p>
                                        <p class="market-line"><b>Ano:</b> {ano_item}</p>
                                        <p class="market-line"><b>Disponíveis:</b> {estoque_item_texto}</p>
                                        <div class="market-price-grid">
                                            <div class="market-price"><small>Preço GarageHub</small><strong>{money(item.get('valor') or 0)}</strong></div>
                                            <div class="market-price"><small>Estimado</small><strong>{money(item.get('valor_estimado') or item.get('valor') or 0)}</strong></div>
                                            <div class="market-price"><small>Disponíveis</small><strong>{estoque_item_texto}</strong></div>
                                        </div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                                col_btn1, col_btn2 = st.columns([1, 1])
                                with col_btn1:
                                    if st.button("🛒 Reservar", key=f"loja_pedir_{item.get('id')}", use_container_width=True):
                                        try:
                                            if pedido_aberto_existe(usuario["id"], item.get("id")):
                                                st.warning("Você já possui um pedido em aberto para esta mini. Confira a aba Meus pedidos.")
                                            else:
                                                criar_pedido_loja(usuario["id"], item)
                                                baixar_estoque_loja_item(item, 1)
                                                st.success("Pedido enviado ao admin. Acompanhe o andamento na aba Meus pedidos.")
                                                st.rerun()
                                        except Exception:
                                            st.error("Não foi possível criar o pedido. Confirme se a tabela pedidos existe no Supabase.")
                                with col_btn2:
                                    st.button("❤️ Favorito", key=f"loja_fav_{item.get('id')}", use_container_width=True)

                st.info("Fluxo oficial: você reserva/comprar pela loja, o admin confirma o pedido, registra o pagamento e lança a mini na sua garagem oficial.")

        with aba_pre_venda_cliente:
            render_pre_vendas_cliente(usuario)

        with aba_rifas_cliente:
            render_rifas_cliente(usuario)

        with aba_meus_pedidos:
            st.markdown("""
            <div class="store-callout">
                <h3>📦 Meus pedidos</h3>
                <p>Acompanhe aqui suas reservas, compras pendentes, pedidos pagos e minis já concluídas.</p>
            </div>
            """, unsafe_allow_html=True)

            try:
                meus_pedidos = buscar_pedidos(usuario["id"])
            except Exception:
                meus_pedidos = []
                st.error("Tabela pedidos ainda não existe. Avise o administrador.")

            if not meus_pedidos:
                st.info("Você ainda não possui pedidos na loja.")
            else:
                total_pedidos = len(meus_pedidos)
                pedidos_abertos = len([p for p in meus_pedidos if (p.get("status") or "solicitado") in ["solicitado", "pendente", "pago"]])
                pedidos_concluidos = len([p for p in meus_pedidos if (p.get("status") or "") == "concluido"])
                valor_em_aberto = sum(float(p.get("valor") or 0) for p in meus_pedidos if (p.get("status") or "solicitado") in ["solicitado", "pendente", "pago"])

                p1, p2, p3, p4 = st.columns(4)
                with p1:
                    st.markdown(f'<div class="metric-card"><div class="metric-icon">📦</div><h2>{total_pedidos}</h2><p>Total pedidos</p></div>', unsafe_allow_html=True)
                with p2:
                    st.markdown(f'<div class="metric-card"><div class="metric-icon">🟡</div><h2>{pedidos_abertos}</h2><p>Em aberto</p></div>', unsafe_allow_html=True)
                with p3:
                    st.markdown(f'<div class="metric-card"><div class="metric-icon">🏁</div><h2>{pedidos_concluidos}</h2><p>Concluídos</p></div>', unsafe_allow_html=True)
                with p4:
                    st.markdown(f'<div class="metric-card"><div class="metric-icon">💰</div><h2>{money(valor_em_aberto)}</h2><p>Valor em aberto</p></div>', unsafe_allow_html=True)

                st.divider()
                for ped in meus_pedidos:
                    status_ped = ped.get("status") or "solicitado"
                    st.markdown(f"""
                    <div class="user-card">
                        <div class="user-head">
                            <div>
                                <div class="user-name">#{html.escape(str(ped.get('id')))} — {html.escape(str(ped.get('nome') or 'Mini'))}</div>
                                <div class="user-email">{html.escape(str(ped.get('marca') or ''))} — {html.escape(str(ped.get('serie') or ''))}</div>
                            </div>
                            <div>
                                <span class="badge-status badge-pedido-{html.escape(str(status_ped))}">{html.escape(str(status_ped))}</span>
                                <span class="badge-raridade badge-{html.escape(str(ped.get('raridade') or 'Comum'))}">{html.escape(str(ped.get('raridade') or 'Comum'))}</span>
                            </div>
                        </div>
                        <div class="user-info-grid">
                            <div class="user-info-item"><small>Valor</small><strong>{money(ped.get('valor') or 0)}</strong></div>
                            <div class="user-info-item"><small>Ano</small><strong>{html.escape(str(ped.get('ano') or '-'))}</strong></div>
                            <div class="user-info-item"><small>Observação</small><strong>{html.escape(str(ped.get('observacoes') or '-'))}</strong></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if status_ped in ["solicitado", "pendente", "aguardando_pix"]:
                        if status_ped == "aguardando_pix":
                            st.markdown(pix_card_html(ped, "Seu Pix para pagamento"), unsafe_allow_html=True)
                        c_pix, c_cancel = st.columns([1.4, 1])
                        with c_pix:
                            if st.button("💳 Gerar / ver Pix", key=f"cli_gerar_pix_{ped['id']}"):
                                try:
                                    atualizar_pedido(ped["id"], {"status": "aguardando_pix", "observacoes": f"Pix gerado pelo cliente. {gerar_pix_copia_cola(ped)}"})
                                    st.success("Pix gerado. Após pagar, avise o admin para confirmar e lançar na garagem.")
                                    st.rerun()
                                except Exception:
                                    st.error("Não foi possível gerar o Pix agora.")
                        with c_cancel:
                            if st.button("Cancelar solicitação", key=f"cli_cancelar_pedido_{ped['id']}"):
                                try:
                                    atualizar_pedido(ped["id"], {"status": "cancelado"})
                                    if ped.get("loja_mini_id"):
                                        atualizar_loja_mini(ped.get("loja_mini_id"), {"status": "disponivel"})
                                    st.success("Pedido cancelado.")
                                    st.rerun()
                                except Exception:
                                    st.error("Não foi possível cancelar o pedido.")


        with aba_hall_cliente:
            st.markdown("""
            <div class="store-callout">
                <h3>🏆 Seu Hall da Fama</h3>
                <p>Suas minis mais especiais entram aqui automaticamente por raridade, valor ou destaque.</p>
            </div>
            """, unsafe_allow_html=True)
            minis_hall = buscar_minis(usuario["id"])
            hall = [m for m in minis_hall if (m.get("raridade") in ["RLC", "STH", "Chase"] or m.get("tipo_mini") in ["presente", "premio", "vip"] or float(m.get("valor_estimado") or 0) >= 100)]
            hall = sorted(hall, key=lambda m: float(m.get("valor_estimado") or 0), reverse=True)
            if not hall:
                st.info("Seu Hall da Fama ainda está vazio. Quando o admin lançar minis raras, presentes ou destaques, elas aparecerão aqui.")
            else:
                cards = []
                for mini in hall:
                    raridade = html.escape(str(mini.get("raridade") or "Comum"))
                    cards.append(
                        f'<div class="mini-card hall-glow">'
                        f'{imagem_html(get_foto_item(mini))}'
                        f'<div class="mini-body">'
                        f'<h3 class="mini-title">🏆 {html.escape(str(mini.get("nome") or "Mini"))}</h3>'
                        f'<span class="badge-raridade badge-{raridade}">{raridade}</span>'
                        f'<span class="badge-destaque">Hall da Fama</span>'
                        f'<p class="mini-meta"><b>Série:</b> {html.escape(str(mini.get("serie") or "-"))}</p>'
                        f'<div class="price-box"><small>Valor estimado</small><strong>{money(mini.get("valor_estimado") or 0)}</strong></div>'
                        f'</div></div>'
                    )
                st.markdown('<div class="garage-grid">' + ''.join(cards) + '</div>', unsafe_allow_html=True)

        with aba_ranking_cliente:
            st.markdown("""
            <div class="store-callout">
                <h3>👑 Ranking GarageHub</h3>
                <p>Ranking interno baseado nas compras pagas e minis oficiais lançadas pelo admin.</p>
            </div>
            """, unsafe_allow_html=True)
            try:
                todos_usuarios_rank = listar_usuarios()
                todos_minis_rank = buscar_todas_minis()
                clientes_rank = {u.get("id"): u for u in todos_usuarios_rank if u.get("tipo") != "admin"}
                ranking = {}
                for mini in todos_minis_rank:
                    if (mini.get("status_pagamento") or "pendente") == "pago":
                        uid = mini.get("usuario_id")
                        ranking.setdefault(uid, {"valor": 0.0, "qtd": 0})
                        ranking[uid]["valor"] += float(mini.get("valor_pago") or 0)
                        ranking[uid]["qtd"] += 1
                ranking_ordenado = sorted(ranking.items(), key=lambda item: item[1]["valor"], reverse=True)
                if not ranking_ordenado:
                    st.info("Ranking ainda sem compras pagas.")
                else:
                    for pos, (uid, dados_rank) in enumerate(ranking_ordenado[:10], start=1):
                        cli = clientes_rank.get(uid, {})
                        marcador = "👑 Você" if uid == usuario.get("id") else ""
                        st.markdown(f"""
                        <div class="user-card">
                            <div class="user-head">
                                <div>
                                    <div class="user-name">#{pos} — {html.escape(str(cli.get('nome') or 'Cliente'))} {marcador}</div>
                                    <div class="user-email">{html.escape(str(cli.get('email') or '-'))}</div>
                                </div>
                                <span class="badge-destaque">Top comprador</span>
                            </div>
                            <div class="user-info-grid">
                                <div class="user-info-item"><small>Total pago</small><strong>{money(dados_rank['valor'])}</strong></div>
                                <div class="user-info-item"><small>Minis pagas</small><strong>{dados_rank['qtd']}</strong></div>
                                <div class="user-info-item"><small>Nível</small><strong>{html.escape(str(cli.get('nivel_cliente') or 'comum')).upper()}</strong></div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            except Exception:
                st.error("Não foi possível montar o ranking agora.")

            st.divider()
            render_gamificacao_cliente(usuario)

        with aba_carteirinha_qr:
            nivel = usuario.get("nivel_cliente") or "comum"
            st.markdown(f"""
            <div class="qr-card">
                <h2>🎫 Carteirinha Digital GarageHub</h2>
                <p><strong>{html.escape(str(usuario.get('nome') or 'Cliente'))}</strong></p>
                <div class="qr-box"></div>
                <p>Código: <strong>{html.escape(str(usuario.get('codigo_membro') or '-'))}</strong></p>
                <p>Nível: <strong>{'MEMBRO VIP' if nivel == 'vip' else 'CLIENTE COMUM'}</strong></p>
                <p>Use este QR visual como base da carteirinha. A próxima etapa pode gerar QR real com link público do perfil.</p>
            </div>
            """, unsafe_allow_html=True)

        with aba_lab_cliente:
            st.markdown("""
            <div class="store-callout">
                <h3>🧪 Lab IA/Pix</h3>
                <p>Área preparada para scanner IA, pagamento Pix, notificações e recursos mobile.</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div class="feature-grid">
                <div class="lab-card"><h3>📱 Scanner IA</h3><p>Futuro: apontar a câmera para identificar mini, raridade e dados.</p></div>
                <div class="lab-card"><h3>💳 Pix assistido</h3><p>Agora: cliente gera Pix no pedido e admin confirma para lançar a mini na garagem.</p></div>
                <div class="lab-card"><h3>🔔 Notificações</h3><p>Futuro: avisos de pedido aprovado, pagamento e entrega na garagem.</p></div>
            </div>
            """, unsafe_allow_html=True)



        # =========================
        # ABA PAGAMENTOS CLIENTE
        # =========================
        with aba_pagamentos_cliente:
            try:
                pedidos_pag = buscar_pedidos(usuario["id"])
            except Exception:
                pedidos_pag = []
            render_checkout_real_visual(pedidos_pag)
            st.markdown('<div class="checkout-box"><h3>📎 Comprovante</h3><p>Estrutura pronta para próxima versão: upload de comprovante e validação pelo admin.</p></div>', unsafe_allow_html=True)

        # =========================
        # ABA PERFIL CLIENTE
        # =========================
        with aba_perfil_cliente:
            minis_perfil = buscar_minis(usuario["id"])
            render_perfil_publico(usuario, minis_perfil)
            st.markdown('<div class="pro-grid"><div class="pro-card"><h3>❤️ Favoritos</h3><p>Preparado para salvar minis favoritas da loja.</p></div><div class="pro-card"><h3>🏆 Ranking pessoal</h3><p>Mostra posição e conquistas do colecionador.</p></div><div class="pro-card"><h3>🔗 Compartilhar</h3><p>Base para tornar a coleção pública.</p></div></div>', unsafe_allow_html=True)

        # =========================
        # ABA MOBILE CLIENTE
        # =========================
        with aba_mobile_cliente:
            render_mobile_preview(usuario)

        # =========================
        # ABA NOTIFICAÇÕES CLIENTE
        # =========================
        with aba_notif_cliente:
            try:
                pedidos_user_notif = buscar_pedidos(usuario["id"])
            except Exception:
                pedidos_user_notif = []
            render_notificacoes_demo(usuario, pedidos_user_notif)
            render_timeline_pedidos(pedidos_user_notif)

        # =========================
        # ABA SCANNER IA CLIENTE
        # =========================
        with aba_scanner_cliente:
            render_scanner_ia_demo()
            st.info("Scanner em modo assistido/local. Para identificação automática real, a próxima etapa técnica é conectar IA de visão + catálogo de referência.")

        with aba_garagem:
            col_cliente_refresh_1, col_cliente_refresh_2 = st.columns([1, 3])
            with col_cliente_refresh_1:
                if st.button("🔄 Atualizar garagem", use_container_width=True, key=f"cliente_refresh_garagem_{usuario.get('id')}"):
                    try:
                        st.cache_data.clear()
                    except Exception:
                        pass
                    try:
                        st.cache_resource.clear()
                    except Exception:
                        pass
                    st.rerun()
            with col_cliente_refresh_2:
                st.caption("Clique aqui quando o admin incluir pré-vendas antigas ou novas minis na sua garagem.")

            minis = buscar_minis(usuario["id"])

            if not minis:
                st.info("Nenhuma mini cadastrada ainda.")
            else:
                total_minis = len(minis)
                total_pago = sum(float(m.get("valor_pago") or 0) for m in minis)
                total_estimado = sum(float(m.get("valor_estimado") or 0) for m in minis)
                valorizacao_total = total_estimado - total_pago
                rlc_sth = len([m for m in minis if m.get("raridade") in ["RLC", "STH", "Chase"]])
                minis_pendentes = qtd_pendente_pagamento(minis)
                valor_pendente = total_pendente_pagamento(minis)

                m1, m2, m3, m4, m5 = st.columns(5)
                with m1:
                    st.markdown(f'<div class="metric-card"><h2>{total_minis}</h2><p>Minis</p></div>', unsafe_allow_html=True)
                with m2:
                    st.markdown(f'<div class="metric-card"><h2>{money(total_pago)}</h2><p>Total pago</p></div>', unsafe_allow_html=True)
                with m3:
                    st.markdown(f'<div class="metric-card"><h2>{money(total_estimado)}</h2><p>Estimado</p></div>', unsafe_allow_html=True)
                with m4:
                    st.markdown(f'<div class="metric-card"><h2>{money(valorizacao_total)}</h2><p>Valorização</p></div>', unsafe_allow_html=True)
                with m5:
                    st.markdown(f'<div class="metric-card metric-pendente"><h2>{minis_pendentes}</h2><p>Pendentes</p><small>{money(valor_pendente)}</small></div>', unsafe_allow_html=True)

                st.markdown("#### Filtros")
                f1, f2, f3 = st.columns([2, 1, 1])
                with f1:
                    busca = st.text_input("Buscar por nome, série ou marca", key="filtro_busca")
                with f2:
                    raridades = ["Todas"] + sorted(list(set([m.get("raridade") or "Sem raridade" for m in minis])))
                    filtro_raridade = st.selectbox("Raridade", raridades, key="filtro_raridade")
                with f3:
                    ordenacao = st.selectbox("Ordenar", ["Mais recentes", "Maior valor", "Maior valorização", "Nome A-Z"], key="ordenacao")

                filtrados = minis[:]
                if busca:
                    b = busca.lower().strip()
                    filtrados = [m for m in filtrados if b in str(m.get("nome", "")).lower() or b in str(m.get("serie", "")).lower() or b in str(m.get("marca", "")).lower()]
                if filtro_raridade != "Todas":
                    filtrados = [m for m in filtrados if (m.get("raridade") or "Sem raridade") == filtro_raridade]

                if ordenacao == "Maior valor":
                    filtrados = sorted(filtrados, key=lambda m: float(m.get("valor_estimado") or 0), reverse=True)
                elif ordenacao == "Maior valorização":
                    filtrados = sorted(filtrados, key=lambda m: float(m.get("valor_estimado") or 0) - float(m.get("valor_pago") or 0), reverse=True)
                elif ordenacao == "Nome A-Z":
                    filtrados = sorted(filtrados, key=lambda m: str(m.get("nome") or ""))

                st.caption(f"Exibindo {len(filtrados)} mini(s). Destaques RLC/STH/Chase: {rlc_sth}")

                # Renderização segura da garagem: usa componentes nativos do Streamlit
                # para impedir que HTML salvo acidentalmente em algum campo apareça na tela.
                def limpar_campo_visual(valor, padrao="-"):
                    texto = str(valor or "").strip()
                    if not texto:
                        return padrao
                    # Se algum campo veio contaminado com HTML do card antigo, esconde.
                    suspeitos = ["<div", "</div", "<p", "</p", "class=", "price-row", "mini-meta", "mini-card"]
                    if any(s in texto.lower() for s in suspeitos):
                        return padrao
                    texto = re.sub(r"<[^>]*>", "", texto)
                    return html.unescape(texto).strip() or padrao

                if not filtrados:
                    st.warning("Nenhuma mini encontrada com esses filtros.")
                else:
                    for i in range(0, len(filtrados), 3):
                        cols_mini = st.columns(3)

                        for col_mini, mini in zip(cols_mini, filtrados[i:i+3]):
                            with col_mini:
                                nome = limpar_campo_visual(mini.get("nome"), "Mini sem nome")
                                marca = limpar_campo_visual(mini.get("marca"), "-")
                                serie = limpar_campo_visual(mini.get("serie"), "-")
                                ano = limpar_campo_visual(mini.get("ano"), "-")
                                raridade = limpar_campo_visual(mini.get("raridade"), "Comum")
                                status_pagamento = limpar_campo_visual(mini.get("status_pagamento"), "pendente").upper()
                                tipo_mini = limpar_campo_visual(mini.get("tipo_mini"), "compra").upper()
                                destaque_cliente = limpar_campo_visual(mini.get("destaque_cliente"), "")
                                valor_pago = float(mini.get("valor_pago") or 0)
                                valor_estimado = float(mini.get("valor_estimado") or 0)
                                valorizacao = valor_estimado - valor_pago
                                foto = str(get_foto_item(mini) or "")

                                if any(s in foto.lower() for s in ["<div", "<p", "class=", "mini-meta", "price-row"]):
                                    foto = ""

                                with st.container(border=True):
                                    src_foto = foto_src(foto)

                                    if src_foto:
                                        st.markdown(
                                            f"""
                                            <div class="garage-photo-box">
                                                <img src="{html.escape(src_foto, quote=True)}" loading="lazy" referrerpolicy="no-referrer">
                                            </div>
                                            """,
                                            unsafe_allow_html=True
                                        )
                                    else:
                                        st.markdown(
                                            "<div class='garage-photo-box garage-empty'>🏎️</div>",
                                            unsafe_allow_html=True
                                        )

                                    st.markdown(f"### {html.escape(nome)}")

                                    badge_html = f"""
                                    <span class="badge-raridade badge-{html.escape(raridade)}">{html.escape(raridade)}</span>
                                    <span class="badge-status badge-status-{html.escape(status_pagamento.lower())}">{html.escape(status_pagamento)}</span>
                                    <span class="badge-tipo">{html.escape(tipo_mini)}</span>
                                    """

                                    if destaque_cliente:
                                        badge_html += f'<span class="badge-destaque">{html.escape(destaque_cliente)}</span>'

                                    st.markdown(badge_html, unsafe_allow_html=True)

                                    st.markdown(f"**Marca:** {html.escape(marca)}")
                                    st.markdown(f"**Série:** {html.escape(serie)}")
                                    st.markdown(f"**Ano:** {html.escape(ano)}")

                                    classe_val = "valor-pos" if valorizacao >= 0 else "valor-neg"

                                    st.markdown(f"""
                                    <div class="price-row" style="margin-top:16px;">
                                        <div class="price-box"><small>Pago</small><strong>{money(valor_pago)}</strong></div>
                                        <div class="price-box"><small>Estimado</small><strong>{money(valor_estimado)}</strong></div>
                                    </div>
                                    <div class="price-box" style="margin-top:10px;">
                                        <small>Valorização</small>
                                        <strong class="{classe_val}">{money(valorizacao)}</strong>
                                    </div>
                                    """, unsafe_allow_html=True)

                st.divider()
                st.info("A sua garagem é oficial: somente o admin pode incluir, alterar ou remover minis compradas/presentes.")


# =========================
# ADMIN - LOGIN MANAGER
# =========================
def render_admin_login_manager():
    st.markdown("""
    <div class="admin-work-card">
        <h3>🔐 Gestão de acesso dos clientes</h3>
        <p>
            Corrija emails fake, resete senhas e prepare clientes importados para primeiro acesso.
        </p>
    </div>
    """, unsafe_allow_html=True)

    usuarios = listar_usuarios()

    for u in usuarios:

        with st.expander(f"👤 {u.get('nome')} • {u.get('email')}"):

            novo_email = st.text_input(
                "Email do cliente",
                value=u.get("email",""),
                key=f"email_admin_{u.get('id')}"
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 Atualizar email", key=f"btn_email_{u.get('id')}"):
                    atualizar_email_cliente(
                        u.get("id"),
                        novo_email
                    )
                    st.success("Email atualizado.")

            with col2:
                if st.button("🔁 Resetar senha", key=f"btn_reset_{u.get('id')}"):
                    resetar_senha_cliente(u.get("id"))
                    st.success("Senha marcada como primeiro acesso.")
