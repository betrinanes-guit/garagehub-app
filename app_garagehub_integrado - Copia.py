import base64
import html
import mimetypes
import re
import hashlib
from pathlib import Path
from datetime import datetime

import streamlit as st
from supabase import create_client

st.set_page_config(
    page_title="GarageHub - Garagem Hot Wheels",
    page_icon="🏁",
    layout="wide"
)

BASE_DIR = Path(__file__).parent
BANNER_PATH = BASE_DIR / "assets" / "banner.jpg"
STORAGE_BUCKET = "fotos-minis"

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# =========================
# UTILITÁRIOS
# =========================
def img_base64(path):
    path = Path(path)
    if not path.exists():
        return ""
    return base64.b64encode(path.read_bytes()).decode()


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


def foto_src(foto):
    """Aceita URL pública ou caminho local e devolve um src pronto para HTML."""
    if not foto:
        return ""
    foto = str(foto)
    if is_url(foto):
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
        return f'<img src="{src}" class="{classe}">'
    return '<div class="mini-img empty-img">🏎️</div>'


def perfil_html(foto):
    src = foto_src(foto)
    if src:
        return f'<img src="{src}" class="perfil-card-img">'
    return '<div class="perfil-placeholder">👤</div>'


def upload_storage(uploaded_file, pasta, prefixo):
    """Tenta salvar no Supabase Storage. Se falhar, salva local para não travar o app."""
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
        return supabase.storage.from_(STORAGE_BUCKET).get_public_url(nome)
    except Exception:
        pasta_local = BASE_DIR / "assets" / pasta
        pasta_local.mkdir(parents=True, exist_ok=True)
        arquivo = pasta_local / Path(nome).name
        arquivo.write_bytes(dados)
        return str(arquivo)


# =========================
# BANCO / SUPABASE
# =========================
def login(email, senha):
    resp = (
        supabase.table("usuarios")
        .select("*")
        .eq("email", email.strip())
        .eq("senha", senha)
        .execute()
    )
    return resp.data[0] if resp.data else None


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
                   status_pagamento="pendente", tipo_mini="compra", destaque_cliente=""):
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
        "destaque_cliente": destaque_cliente or ""
    }

    try:
        supabase.table("minis").insert(dados).execute()
    except Exception:
        # Fallback para ambientes onde as novas colunas ainda não existem.
        dados.pop("status_pagamento", None)
        dados.pop("tipo_mini", None)
        dados.pop("destaque_cliente", None)
        supabase.table("minis").insert(dados).execute()


def buscar_todas_minis():
    return supabase.table("minis").select("*").order("criado_em", desc=True).execute().data


def atualizar_mini(mini_id, dados):
    supabase.table("minis").update(dados).eq("id", mini_id).execute()


def excluir_mini(mini_id):
    supabase.table("minis").delete().eq("id", mini_id).execute()


def buscar_loja_minis(apenas_disponiveis=False):
    query = supabase.table("loja_minis").select("*")
    if apenas_disponiveis:
        query = query.eq("status", "disponivel")
    return query.order("criado_em", desc=True).execute().data


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
        "compra",
        ""
    )

    atualizar_pedido(pedido["id"], {"status": "concluido"})

    if pedido.get("loja_mini_id"):
        try:
            atualizar_loja_mini(pedido.get("loja_mini_id"), {"status": "vendido"})
        except Exception:
            pass

    return True, "Pedido pago, mini lançada na garagem e item marcado como vendido."


def atualizar_nivel_cliente(usuario_id, nivel_cliente):
    supabase.table("usuarios").update({"nivel_cliente": nivel_cliente}).eq("id", usuario_id).execute()


def listar_usuarios():
    return supabase.table("usuarios").select("*").order("criado_em", desc=True).execute().data


def atualizar_status(usuario_id, status):
    supabase.table("usuarios").update({"status": status}).eq("id", usuario_id).execute()


def criar_usuario(nome, email, senha, telefone, cidade, estado, instagram, foto_perfil_url, codigo_convite=""):
    if not nome or not email or not senha:
        return False, "Preencha nome, e-mail e senha."

    codigo_membro = f"GHW-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    dados = {
        "nome": nome.strip(),
        "email": email.strip(),
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
    if not nome or not email or not senha:
        return False, "Preencha nome, e-mail e senha do cliente."

    codigo_membro = f"GHW-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    try:
        supabase.table("usuarios").insert({
            "nome": nome.strip(),
            "email": email.strip(),
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
        }).execute()
        return True, "Cliente criado com sucesso."
    except Exception as e:
        return False, f"Erro ao criar cliente: {e}"


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
    background:
        radial-gradient(circle at top left, rgba(250,204,21,.14), transparent 34%),
        linear-gradient(160deg, rgba(17,24,39,.98), rgba(2,6,23,.99));
    border:1px solid rgba(250,204,21,.24);
    border-radius:26px;
    overflow:hidden;
    margin-bottom:18px;
    box-shadow:0 20px 52px rgba(0,0,0,.36), 0 0 30px rgba(250,204,21,.06);
    transition:.25s ease;
}
.market-card:hover {
    transform: translateY(-4px);
    border-color: rgba(250,204,21,.55);
    box-shadow:0 26px 70px rgba(0,0,0,.46), 0 0 36px rgba(250,204,21,.13);
}
.market-img, .market-empty {
    width:100%;
    height:245px;
    object-fit:cover;
    background:#020617;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:58px;
    border-bottom:1px solid rgba(148,163,184,.16);
}
.market-body { padding:18px; }
.market-name {
    margin:0 0 8px;
    color:#fff;
    font-size:21px;
    font-weight:950;
    line-height:1.15;
}
.market-line { color:#cbd5e1; font-size:13px; font-weight:850; margin:3px 0; }
.market-price {
    margin-top:14px;
    padding:13px;
    background:rgba(15,23,42,.78);
    border:1px solid rgba(148,163,184,.15);
    border-radius:17px;
}
.market-price small { color:#94a3b8; font-weight:900; }
.market-price strong { display:block; margin-top:3px; color:#facc15; font-size:24px; font-weight:950; }
.market-tags { margin: 8px 0 10px; }
.market-tag {
    display:inline-block;
    margin:4px 5px 4px 0;
    padding:6px 10px;
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
    float:right;
    font-size:20px;
    filter: drop-shadow(0 0 10px rgba(239,68,68,.35));
}
@media (max-width: 900px) {
    .market-stats { grid-template-columns:1fr; }
    .market-title { font-size:32px; }
    .market-img, .market-empty { height:210px; }
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
    # Scanner IA Lab: câmera/upload, prévia e sugestão editável.
    usuario_atual = st.session_state.get("usuario") or {}
    is_admin = usuario_atual.get("tipo") == "admin"

    st.markdown('''
    <div class="scanner-hero">
        <div class="scanner-kicker">🤖 Scanner IA Lab</div>
        <h2>Scanner de Miniaturas</h2>
        <p>Envie uma foto ou use a câmera. Nesta versão o app faz uma leitura assistida/local com base no nome do arquivo e nas observações. A área já fica pronta para conectar uma IA de visão depois.</p>
    </div>
    <div class="pro-grid">
        <div class="scanner-step"><h3>📷 1. Captura</h3><p>Foto da mini, embalagem ou blister.</p></div>
        <div class="scanner-step"><h3>🧠 2. Sugestão</h3><p>Nome, marca, série, ano, raridade e preço sugerido.</p></div>
        <div class="scanner-step"><h3>🏁 3. Ação</h3><p>Admin publica na loja ou lança na garagem. Cliente usa como consulta.</p></div>
    </div>
    ''', unsafe_allow_html=True)

    modo = st.radio("Modo de captura", ["Enviar imagem", "Usar câmera"], horizontal=True, key="scanner_modo_captura")
    entrada_img = None
    if modo == "Usar câmera":
        entrada_img = st.camera_input("Aponte a câmera para a mini", key="scanner_camera_real")
    else:
        entrada_img = st.file_uploader("Enviar foto da mini", type=["jpg", "jpeg", "png"], key="scanner_upload_real")

    obs = st.text_input(
        "Observação para ajudar o scanner",
        placeholder="Ex: Gulf, Kaido R34, STH, RLC, Fast & Furious, ano 2024...",
        key="scanner_obs_texto"
    )

    if entrada_img is not None:
        st.image(entrada_img, caption="Imagem recebida pelo Scanner IA Lab", use_container_width=True)
        sugestao = detectar_mini_por_texto(getattr(entrada_img, "name", "scanner"), obs)
    else:
        sugestao = detectar_mini_por_texto("", obs)
        st.info("Envie uma foto ou digite uma observação para gerar a sugestão do scanner.")

    st.markdown(f'''
    <div class="scanner-result">
        <div class="scanner-score">{sugestao['confianca']}%</div>
        <h3>Resultado sugerido</h3>
        <p><b>{html.escape(sugestao['nome'])}</b> • {html.escape(sugestao['marca'])} • {html.escape(sugestao['raridade'])}</p>
        <p>Série: <b>{html.escape(sugestao['serie'] or 'A confirmar')}</b> • Ano: <b>{html.escape(sugestao['ano'] or 'A confirmar')}</b> • Valor sugerido: <b>{money(sugestao['valor'])}</b></p>
    </div>
    ''', unsafe_allow_html=True)

    with st.expander("Ajustar dados sugeridos pelo scanner", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            s_nome = st.text_input("Nome identificado", value=sugestao["nome"], key="scanner_nome_sugerido")
            s_marca = st.text_input("Marca", value=sugestao["marca"], key="scanner_marca_sugerida")
            s_serie = st.text_input("Série", value=sugestao["serie"], key="scanner_serie_sugerida")
            s_ano = st.text_input("Ano", value=sugestao["ano"], key="scanner_ano_sugerido")
        with c2:
            opcoes_r = ["Comum", "TH", "STH", "Premium", "RLC", "Chase", "Especial"]
            s_raridade = st.selectbox("Raridade", opcoes_r, index=opcoes_r.index(sugestao["raridade"]) if sugestao["raridade"] in opcoes_r else 0, key="scanner_raridade_sugerida")
            s_valor = st.number_input("Preço de venda sugerido", min_value=0.0, step=1.0, value=float(sugestao["valor"]), key="scanner_valor_sugerido")
            s_estimado = st.number_input("Valor estimado sugerido", min_value=0.0, step=1.0, value=float(sugestao["valor_estimado"]), key="scanner_estimado_sugerido")
            s_destaque = st.text_input("Destaque", value="Scanner IA Lab", key="scanner_destaque_sugerido")

    if is_admin:
        st.markdown('<div class="checkout-box"><h3>👑 Ações de admin</h3><p>Use o resultado do scanner para publicar na loja ou lançar diretamente na garagem de um cliente.</p></div>', unsafe_allow_html=True)
        ac1, ac2 = st.columns(2)
        with ac1:
            if st.button("🛒 Publicar sugestão na loja", key="scanner_publicar_loja", use_container_width=True):
                foto_url = upload_storage(entrada_img, "scanner", s_nome) if entrada_img is not None else ""
                try:
                    cadastrar_loja_mini(s_nome, s_marca, s_serie, s_ano, s_raridade, s_valor, s_estimado, foto_url, "disponivel", s_destaque)
                    st.success("Mini publicada na loja usando a sugestão do Scanner IA Lab.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Não consegui publicar na loja. Verifique a tabela loja_minis. Detalhe: {e}")
        with ac2:
            try:
                clientes_scanner = [u for u in listar_usuarios() if u.get("tipo") != "admin"]
            except Exception:
                clientes_scanner = []
            if clientes_scanner:
                mapa_clientes = {f"{c.get('nome','')} — {c.get('email','')}": c for c in clientes_scanner}
                cliente_label = st.selectbox("Cliente para lançar na garagem", list(mapa_clientes.keys()), key="scanner_cliente_garagem")
                if st.button("🏎️ Lançar na garagem do cliente", key="scanner_lancar_garagem", use_container_width=True):
                    foto_url = upload_storage(entrada_img, "scanner", s_nome) if entrada_img is not None else ""
                    cliente_sel = mapa_clientes[cliente_label]
                    cadastrar_mini(cliente_sel["id"], s_nome, s_marca, s_serie, s_ano, s_raridade, s_valor, s_estimado, foto_url, "pago", "scanner/admin", "Scanner IA")
                    st.success("Mini lançada na garagem do cliente a partir do Scanner IA Lab.")
                    st.rerun()
            else:
                st.info("Cadastre clientes para lançar direto na garagem.")
    else:
        st.markdown('<div class="checkout-box"><h3>🏁 Consulta do colecionador</h3><p>Use o scanner para consultar a mini. Para adicionar oficialmente na garagem, o admin precisa validar e lançar.</p></div>', unsafe_allow_html=True)
        st.caption("Na próxima etapa, essa foto poderá virar uma solicitação automática para o admin validar.")

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

            email = st.text_input("E-mail", key="login_email", placeholder="seuemail@exemplo.com")
            senha = st.text_input("Senha", type="password", key="login_senha", placeholder="Digite sua senha")

            if st.button("Entrar na GarageHub", key="btn_login", use_container_width=True):
                usuario = login(email, senha)
                if usuario:
                    if usuario.get("status") != "ativo":
                        st.error("Sua garagem está bloqueada. Fale com o administrador.")
                    else:
                        st.session_state.usuario = usuario
                        st.rerun()
                else:
                    st.error("E-mail ou senha inválidos.")

            st.markdown('<div class="login-note">ADM inicial: <b>admin@garagehub.com</b> / <b>admin123</b></div>', unsafe_allow_html=True)

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
                foto_url = upload_storage(foto_perfil, "perfis", novo_email)
                ok, msg = criar_usuario(nome, novo_email, nova_senha, telefone, cidade, estado, instagram, foto_url)
                if ok:
                    st.success(msg)
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

        st.markdown("""
        <div class="feature-grid">
            <div class="feature-card"><h3>🧭 SaaS Navigation</h3><p>Menu lateral premium para dar sensação de plataforma profissional.</p></div>
            <div class="feature-card"><h3>🛒 Commerce Core</h3><p>Loja, pedidos e garagem integrados no mesmo fluxo comercial.</p></div>
            <div class="feature-card"><h3>👑 VIP Engine</h3><p>Controle de membros, ranking, hall e comunidade em evolução.</p></div>
        </div>
        """, unsafe_allow_html=True)

        usuarios = listar_usuarios()
        clientes = [u for u in usuarios if u.get("tipo") != "admin"]
        todas_minis = buscar_todas_minis()

        total = len(usuarios)
        ativos = len([u for u in usuarios if u.get("status") == "ativo"])
        bloqueados = len([u for u in usuarios if u.get("status") == "bloqueado"])

        total_pago_fin = sum(float(m.get("valor_pago") or 0) for m in todas_minis if (m.get("status_pagamento") or "pendente") == "pago")
        total_pendente_fin = sum(float(m.get("valor_pago") or 0) for m in todas_minis if (m.get("status_pagamento") or "pendente") == "pendente")
        total_reservado_fin = sum(float(m.get("valor_pago") or 0) for m in todas_minis if (m.get("status_pagamento") or "pendente") == "reservado")

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f'<div class="metric-card"><div class="metric-icon">👥</div><h2>{total}</h2><p>Total usuários</p></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="metric-card"><div class="metric-icon">✅</div><h2>{ativos}</h2><p>Ativos</p></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="metric-card"><div class="metric-icon">🔒</div><h2>{bloqueados}</h2><p>Bloqueados</p></div>', unsafe_allow_html=True)
        with m4:
            st.markdown(f'<div class="metric-card"><div class="metric-icon">💰</div><h2>{money(total_pago_fin)}</h2><p>Pago</p></div>', unsafe_allow_html=True)

        aba_clientes, aba_loja, aba_pedidos, aba_minis, aba_financeiro, aba_hall_admin, aba_timeline_admin, aba_sorteios_admin, aba_lab_admin, aba_exec_admin, aba_checkout_admin, aba_notif_admin = st.tabs([
            "👥 Clientes",
            "🛒 Loja",
            "💰 Pedidos",
            "🏎️ Minis",
            "📊 Financeiro",
            "🏆 Hall",
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
                    foto_cliente = upload_storage(adm_foto, "perfis", adm_email)
                    ok, msg = criar_cliente_admin(adm_nome, adm_email, adm_senha, adm_tel, adm_cidade, adm_estado, adm_insta, foto_cliente)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

            st.subheader("Usuários cadastrados")

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
                    st.markdown('<div class="admin-avatar-wrap">' + perfil_html(u.get("foto_perfil_url") or "") + '</div>', unsafe_allow_html=True)
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

                    c1, c2, c3, c4 = st.columns([1, 1, 1, 3])
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
                        st.write("")

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

            with st.expander("Cadastrar mini na loja", expanded=True):
                with st.form("form_admin_loja_mini"):
                    l1, l2 = st.columns(2)
                    with l1:
                        loja_nome = st.text_input("Nome da mini", key="loja_nome")
                        loja_marca = st.text_input("Marca", value="Hot Wheels", key="loja_marca")
                        loja_serie = st.text_input("Série", key="loja_serie")
                        loja_ano = st.text_input("Ano", key="loja_ano")
                        loja_foto = st.file_uploader("Foto da mini", type=["jpg", "jpeg", "png"], key="loja_foto")
                    with l2:
                        loja_raridade = st.selectbox("Raridade", ["Comum", "TH", "STH", "Premium", "RLC", "Chase", "Especial"], key="loja_raridade")
                        loja_valor = st.number_input("Preço de venda", min_value=0.0, step=1.0, key="loja_valor")
                        loja_estimado = st.number_input("Valor estimado", min_value=0.0, step=1.0, key="loja_estimado")
                        loja_status = st.selectbox("Status na loja", ["disponivel", "reservado", "vendido"], key="loja_status")
                        loja_destaque = st.text_input("Destaque", placeholder="Ex: Novidade, Raro, Promoção", key="loja_destaque")

                    if st.form_submit_button("Publicar mini na loja"):
                        if not loja_nome:
                            st.error("Informe o nome da mini.")
                        else:
                            loja_foto_url = upload_storage(loja_foto, "loja", loja_nome)
                            try:
                                cadastrar_loja_mini(loja_nome, loja_marca, loja_serie, loja_ano, loja_raridade, loja_valor, loja_estimado, loja_foto_url, loja_status, loja_destaque)
                                st.success("Mini publicada na loja.")
                                st.rerun()
                            except Exception as e:
                                st.error("Não foi possível salvar na loja. Confirme se a tabela loja_minis existe no Supabase.")

            st.subheader("Minis cadastradas na loja")
            try:
                loja_minis_admin = buscar_loja_minis(apenas_disponiveis=False)
            except Exception:
                loja_minis_admin = []
                st.error("Tabela loja_minis ainda não existe. Rode o SQL informado antes de usar a loja.")

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
                            op_r = ["Comum", "TH", "STH", "Premium", "RLC", "Chase", "Especial"]
                            r_atual = loja_edit.get("raridade") or "Comum"
                            el_raridade = st.selectbox("Raridade", op_r, index=op_r.index(r_atual) if r_atual in op_r else 0, key=f"el_rar_{loja_edit['id']}")
                            el_valor = st.number_input("Preço de venda", min_value=0.0, step=1.0, value=float(loja_edit.get("valor") or 0), key=f"el_valor_{loja_edit['id']}")
                            el_estimado = st.number_input("Valor estimado", min_value=0.0, step=1.0, value=float(loja_edit.get("valor_estimado") or 0), key=f"el_estimado_{loja_edit['id']}")
                            op_st = ["disponivel", "reservado", "vendido"]
                            st_atual = loja_edit.get("status") or "disponivel"
                            el_status = st.selectbox("Status", op_st, index=op_st.index(st_atual) if st_atual in op_st else 0, key=f"el_status_{loja_edit['id']}")
                            el_destaque = st.text_input("Destaque", value=loja_edit.get("destaque") or "", key=f"el_dest_{loja_edit['id']}")

                        sl1, sl2 = st.columns(2)
                        with sl1:
                            salvar_loja = st.form_submit_button("Salvar item da loja")
                        with sl2:
                            excluir_loja_btn = st.form_submit_button("Excluir item da loja")

                        if salvar_loja:
                            nova_foto = loja_edit.get("foto_url") or ""
                            if el_foto is not None:
                                nova_foto = upload_storage(el_foto, "loja", el_nome)
                            atualizar_loja_mini(loja_edit["id"], {
                                "nome": el_nome,
                                "marca": el_marca,
                                "serie": el_serie,
                                "ano": el_ano,
                                "raridade": el_raridade,
                                "valor": el_valor,
                                "valor_estimado": el_estimado,
                                "foto_url": nova_foto,
                                "status": el_status,
                                "destaque": el_destaque,
                            })
                            st.success("Item da loja atualizado.")
                            st.rerun()

                        if excluir_loja_btn:
                            excluir_loja_mini(loja_edit["id"])
                            st.success("Item removido da loja.")
                            st.rerun()

                st.divider()
                for item in loja_minis_admin:
                    st.markdown(f"""
                    <div class="user-card">
                        <div class="user-head">
                            <div>
                                <div class="user-name">{html.escape(str(item.get('nome', '')))}</div>
                                <div class="user-email">{html.escape(str(item.get('marca', '')))} — {html.escape(str(item.get('serie', '')))}</div>
                            </div>
                            <div>
                                <span class="badge-raridade badge-{html.escape(str(item.get('raridade') or 'Comum'))}">{html.escape(str(item.get('raridade') or 'Comum'))}</span>
                                <span class="badge-status badge-loja-{html.escape(str(item.get('status') or 'disponivel'))}">{html.escape(str(item.get('status') or 'disponivel'))}</span>
                            </div>
                        </div>
                        <div class="user-info-grid">
                            <div class="user-info-item"><small>Preço</small><strong>{money(item.get('valor') or 0)}</strong></div>
                            <div class="user-info-item"><small>Estimado</small><strong>{money(item.get('valor_estimado') or 0)}</strong></div>
                            <div class="user-info-item"><small>Destaque</small><strong>{html.escape(str(item.get('destaque') or '-'))}</strong></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # =========================
        # ABA PEDIDOS
        # =========================
        with aba_pedidos:
            st.markdown("""
            <div class="admin-work-card">
                <h3>💰 Pedidos da loja e lançamentos</h3>
                <p>Gerencie solicitações da Loja. Ao clicar em Pago + garagem, o sistema conclui o pedido, lança a mini na garagem do cliente e marca o item como vendido.</p>
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
                            status_pagamento = st.selectbox("Status pagamento", ["pendente", "pago", "reservado", "cancelado"], key="adm_status_pagamento")
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
                                    status_pagamento, tipo_mini, destaque_cliente
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
                            }

                            try:
                                atualizar_mini(mini_edit["id"], dados)
                            except Exception:
                                dados.pop("status_pagamento", None)
                                dados.pop("tipo_mini", None)
                                dados.pop("destaque_cliente", None)
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
                    cards.append(f"""
                    <div class="mini-card hall-glow">
                        {imagem_html(mini.get("foto_url") or "")}
                        <div class="mini-body">
                            <h3 class="mini-title">🏆 {html.escape(str(mini.get('nome') or 'Mini'))}</h3>
                            <span class="badge-raridade badge-{raridade}">{raridade}</span>
                            <span class="badge-destaque">{html.escape(str(mini.get('tipo_mini') or 'Destaque'))}</span>
                            <p class="mini-meta"><b>Dono:</b> {html.escape(str(dono.get('nome') or 'Cliente'))}</p>
                            <p class="mini-meta"><b>Série:</b> {html.escape(str(mini.get('serie') or '-'))}</p>
                            <div class="price-box"><small>Valor estimado</small><strong>{money(mini.get('valor_estimado') or 0)}</strong></div>
                        </div>
                    </div>
                    """)
                st.markdown('<div class="garage-grid">' + ''.join(cards) + '</div>', unsafe_allow_html=True)

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
            st.markdown("""
            <div class="admin-work-card">
                <h3>🎟️ Sorteios e campanhas</h3>
                <p>Área preparada para rifas, sorteios, campanhas VIP e ranking de ganhadores.</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div class="feature-grid">
                <div class="feature-card"><h3>🎁 Sorteio VIP</h3><p>Crie campanhas exclusivas para membros VIP.</p></div>
                <div class="feature-card"><h3>🏆 Top ganhadores</h3><p>Use o campo destaque para marcar clientes premiados.</p></div>
                <div class="feature-card"><h3>🔥 Campanhas</h3><p>Promoções, cupons e ações para girar estoque.</p></div>
            </div>
            """, unsafe_allow_html=True)
            st.info("Próxima versão pode criar tabela sorteios e números automáticos. Esta área já está reservada no painel.")

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
                <div>{perfil_html(usuario.get('foto_perfil_url') or '')}</div>
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

        aba_garagem, aba_loja_cliente, aba_meus_pedidos, aba_hall_cliente, aba_ranking_cliente, aba_carteirinha_qr, aba_lab_cliente, aba_pagamentos_cliente, aba_perfil_cliente, aba_mobile_cliente, aba_notif_cliente, aba_scanner_cliente = st.tabs([
            "🏎️ Minha garagem",
            "🛒 Loja",
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
                loja_disponiveis = buscar_loja_minis(apenas_disponiveis=True)
            except Exception:
                loja_disponiveis = []
                st.error("Loja ainda não configurada. Avise o administrador.")

            if not loja_disponiveis:
                st.info("Nenhuma mini disponível na loja agora.")
            else:
                st.markdown('<div class="market-filter-box">', unsafe_allow_html=True)
                f1, f2, f3 = st.columns([2, 1, 1])
                with f1:
                    busca_loja = st.text_input("🔎 Buscar por nome, marca ou série", key="busca_loja_cliente", placeholder="Ex: Skyline, RLC, Gulf...")
                with f2:
                    raridades_loja = ["Todas"] + sorted(list(set([str(m.get("raridade") or "Comum") for m in loja_disponiveis])))
                    filtro_raridade_loja = st.selectbox("Raridade", raridades_loja, key="filtro_raridade_loja")
                with f3:
                    ordem_loja = st.selectbox("Ordenar", ["Novidades", "Menor preço", "Maior preço", "Nome A-Z"], key="ordem_loja")
                st.markdown('</div>', unsafe_allow_html=True)

                itens_loja = loja_disponiveis[:]
                if busca_loja:
                    b = busca_loja.lower().strip()
                    itens_loja = [m for m in itens_loja if b in str(m.get("nome", "")).lower() or b in str(m.get("marca", "")).lower() or b in str(m.get("serie", "")).lower()]
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

                    for i in range(0, len(itens_loja), 3):
                        cols = st.columns(3)
                        for col, item in zip(cols, itens_loja[i:i+3]):
                            with col:
                                foto_item = item.get("foto_url") or ""
                                img = imagem_html(foto_item, "market-img") if foto_item else '<div class="market-empty">🏎️</div>'
                                nome_item = html.escape(str(item.get("nome") or "Mini"))
                                marca_item = html.escape(str(item.get("marca") or "Hot Wheels"))
                                serie_item = html.escape(str(item.get("serie") or ""))
                                ano_item = html.escape(str(item.get("ano") or ""))
                                raridade_item = html.escape(str(item.get("raridade") or "Comum"))
                                destaque_item = html.escape(str(item.get("destaque") or ""))
                                tag_raro = "market-tag-rare" if raridade_item in ["RLC", "STH", "Chase", "Especial"] else "market-tag-gold"

                                st.markdown(f"""
                                <div class="market-card">
                                    {img}
                                    <div class="market-body">
                                        <div class="favorite-chip">❤️</div>
                                        <h3 class="market-name">{nome_item}</h3>
                                        <div class="market-tags">
                                            <span class="market-tag {tag_raro}">{raridade_item}</span>
                                            <span class="market-tag market-tag-ok">Disponível</span>
                                            <span class="market-tag market-tag-vip">VIP</span>
                                        </div>
                                        <p class="market-line"><b>Marca:</b> {marca_item}</p>
                                        <p class="market-line"><b>Série:</b> {serie_item}</p>
                                        <p class="market-line"><b>Ano:</b> {ano_item}</p>
                                        {'<p class="market-line">🔥 <b>Destaque:</b> ' + destaque_item + '</p>' if destaque_item else ''}
                                        <div class="market-price"><small>Preço GarageHub</small><strong>{money(item.get('valor') or 0)}</strong></div>
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
                                                atualizar_loja_mini(item.get("id"), {"status": "reservado"})
                                                st.success("Pedido enviado ao admin. Acompanhe o andamento na aba Meus pedidos.")
                                                st.rerun()
                                        except Exception:
                                            st.error("Não foi possível criar o pedido. Confirme se a tabela pedidos existe no Supabase.")
                                with col_btn2:
                                    st.button("❤️ Favorito", key=f"loja_fav_{item.get('id')}", use_container_width=True)

                st.info("Fluxo oficial: você reserva/comprar pela loja, o admin confirma o pedido, registra o pagamento e lança a mini na sua garagem oficial.")

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
                    cards.append(f"""
                    <div class="mini-card hall-glow">
                        {imagem_html(mini.get("foto_url") or "")}
                        <div class="mini-body">
                            <h3 class="mini-title">🏆 {html.escape(str(mini.get('nome') or 'Mini'))}</h3>
                            <span class="badge-raridade badge-{raridade}">{raridade}</span>
                            <span class="badge-destaque">Hall da Fama</span>
                            <p class="mini-meta"><b>Série:</b> {html.escape(str(mini.get('serie') or '-'))}</p>
                            <div class="price-box"><small>Valor estimado</small><strong>{money(mini.get('valor_estimado') or 0)}</strong></div>
                        </div>
                    </div>
                    """)
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
            minis = buscar_minis(usuario["id"])

            if not minis:
                st.info("Nenhuma mini cadastrada ainda.")
            else:
                total_minis = len(minis)
                total_pago = sum(float(m.get("valor_pago") or 0) for m in minis)
                total_estimado = sum(float(m.get("valor_estimado") or 0) for m in minis)
                valorizacao_total = total_estimado - total_pago
                rlc_sth = len([m for m in minis if m.get("raridade") in ["RLC", "STH", "Chase"]])

                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.markdown(f'<div class="metric-card"><h2>{total_minis}</h2><p>Minis</p></div>', unsafe_allow_html=True)
                with m2:
                    st.markdown(f'<div class="metric-card"><h2>{money(total_pago)}</h2><p>Total pago</p></div>', unsafe_allow_html=True)
                with m3:
                    st.markdown(f'<div class="metric-card"><h2>{money(total_estimado)}</h2><p>Estimado</p></div>', unsafe_allow_html=True)
                with m4:
                    st.markdown(f'<div class="metric-card"><h2>{money(valorizacao_total)}</h2><p>Valorização</p></div>', unsafe_allow_html=True)

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

                for mini in filtrados:
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
                    foto = str(mini.get("foto_url") or "")
                    if any(s in foto.lower() for s in ["<div", "<p", "class=", "mini-meta", "price-row"]):
                        foto = ""

                    with st.container(border=True):
                        src = foto_src(foto)
                        if src:
                            st.image(src, use_container_width=True)
                        else:
                            st.markdown("<div class='empty-img'>🏎️</div>", unsafe_allow_html=True)

                        st.markdown(f"### {html.escape(nome)}")
                        badge_html = f'''
                        <span class="badge-raridade badge-{html.escape(raridade)}">{html.escape(raridade)}</span>
                        <span class="badge-status badge-status-{html.escape(status_pagamento.lower())}">{html.escape(status_pagamento)}</span>
                        <span class="badge-tipo">{html.escape(tipo_mini)}</span>
                        '''
                        if destaque_cliente:
                            badge_html += f'<span class="badge-destaque">{html.escape(destaque_cliente)}</span>'
                        st.markdown(badge_html, unsafe_allow_html=True)

                        c_info1, c_info2, c_info3 = st.columns(3)
                        c_info1.markdown(f"**Marca:** {html.escape(marca)}")
                        c_info2.markdown(f"**Série:** {html.escape(serie)}")
                        c_info3.markdown(f"**Ano:** {html.escape(ano)}")

                        # Cards de valor sem st.metric (evita erro de módulo dinâmico do Streamlit no navegador)
                        classe_val = "valor-pos" if valorizacao >= 0 else "valor-neg"
                        st.markdown(f"""
                        <div class="price-row" style="margin-top:16px;">
                            <div class="price-box"><small>Pago</small><strong>{money(valor_pago)}</strong></div>
                            <div class="price-box"><small>Estimado</small><strong>{money(valor_estimado)}</strong></div>
                            <div class="price-box"><small>Valorização</small><strong class="{classe_val}">{money(valorizacao)}</strong></div>
                        </div>
                        """, unsafe_allow_html=True)

                st.divider()
                st.info("A sua garagem é oficial: somente o admin pode incluir, alterar ou remover minis compradas/presentes.")
