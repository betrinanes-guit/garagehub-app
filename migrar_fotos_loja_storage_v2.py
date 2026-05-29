import base64
import mimetypes
import re
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except Exception:
    tomllib = None

from supabase import create_client


BUCKET = "fotos-minis"

# IDs confirmados no SQL/print como fotos antigas em base64 na loja_minis.
# Isso evita fazer SELECT com LIKE em uma coluna gigante, que estava dando timeout 57014.
IDS_LOJA_BASE64 = [
    135, 134, 136, 127, 128, 126, 125, 122,
    132, 133, 123, 129, 124, 137, 131, 130
]


def carregar_secrets():
    secrets_path = Path(".streamlit") / "secrets.toml"
    if not secrets_path.exists():
        raise FileNotFoundError(
            "Não encontrei .streamlit/secrets.toml. "
            "Execute este script na mesma pasta do app.py."
        )

    if tomllib is None:
        raise RuntimeError("Este script precisa de Python 3.11+ para ler secrets.toml.")

    with open(secrets_path, "rb") as f:
        secrets = tomllib.load(f)

    url = secrets.get("SUPABASE_URL")
    key = secrets.get("SUPABASE_KEY")

    if not url or not key:
        raise RuntimeError("SUPABASE_URL ou SUPABASE_KEY não encontrados no secrets.toml.")

    return url, key


def slugify(texto):
    texto = str(texto or "mini").lower().strip()
    texto = re.sub(r"[^a-z0-9áàâãéèêíïóôõöúçñ_-]+", "-", texto)
    texto = (
        texto.replace("ç", "c")
        .replace("ã", "a")
        .replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
    )
    texto = re.sub(r"-+", "-", texto).strip("-")
    return texto or "mini"


def extrair_imagem_base64(data_url):
    """
    Recebe algo como:
    data:image/jpeg;base64,/9j/4AAQ...
    e devolve: mime, extensao, bytes
    """
    data_url = str(data_url or "").strip()

    if not data_url.startswith("data:image/"):
        return None, None, None

    match = re.match(r"^data:(image/[^;]+);base64,(.*)$", data_url, flags=re.DOTALL)
    if not match:
        raise ValueError("Formato base64 inválido.")

    mime = match.group(1).strip()
    b64 = match.group(2).strip()

    ext = mimetypes.guess_extension(mime) or ".jpg"
    if ext == ".jpe":
        ext = ".jpg"

    dados = base64.b64decode(b64)
    return mime, ext, dados


def buscar_item_por_id(supabase, loja_id):
    """
    Busca 1 item por vez.
    Não usa LIKE, não usa select geral, não varre tabela com foto_url gigante.
    """
    resp = (
        supabase.table("loja_minis")
        .select("id,nome,foto_url")
        .eq("id", loja_id)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def upload_storage(supabase, loja_id, nome, mime, ext, dados):
    arquivo = f"loja/migradas/{loja_id}_{slugify(nome)}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"

    supabase.storage.from_(BUCKET).upload(
        arquivo,
        dados,
        file_options={
            "content-type": mime,
            "upsert": "true",
        },
    )

    url_publica = supabase.storage.from_(BUCKET).get_public_url(arquivo)
    if not url_publica:
        raise RuntimeError("Upload feito, mas não consegui obter URL pública.")

    return str(url_publica)


def atualizar_foto_url(supabase, loja_id, url_publica):
    supabase.table("loja_minis").update({"foto_url": url_publica}).eq("id", loja_id).execute()


def main():
    print("=== GarageHub - Migração cirúrgica das fotos da Loja para Storage ===")
    print("Estratégia: migrar por ID, 1 por vez, evitando timeout 57014.\n")

    url, key = carregar_secrets()
    supabase = create_client(url, key)

    ok = 0
    pulados = 0
    falhas = 0

    for loja_id in IDS_LOJA_BASE64:
        print(f"\n--- ID {loja_id} ---")

        try:
            item = buscar_item_por_id(supabase, loja_id)

            if not item:
                print("PULADO: item não encontrado.")
                pulados += 1
                continue

            nome = item.get("nome") or f"mini-{loja_id}"
            foto_url = item.get("foto_url") or ""

            if not str(foto_url).startswith("data:image/"):
                print(f"PULADO: {nome} já não está em base64.")
                pulados += 1
                continue

            print(f"Mini: {nome}")
            print(f"Tamanho base64: {len(foto_url):,} caracteres".replace(",", "."))

            mime, ext, dados = extrair_imagem_base64(foto_url)
            print(f"Imagem decodificada: {len(dados):,} bytes | {mime}".replace(",", "."))

            url_publica = upload_storage(supabase, loja_id, nome, mime, ext, dados)
            atualizar_foto_url(supabase, loja_id, url_publica)

            print("OK: migrada para Storage.")
            print(f"URL: {url_publica}")
            ok += 1

            # pequena pausa para não forçar API/Storage
            time.sleep(0.4)

        except Exception as e:
            falhas += 1
            print(f"FALHA no ID {loja_id}: {e}")

    print("\n=== Resumo ===")
    print(f"Migradas com sucesso: {ok}")
    print(f"Puladas: {pulados}")
    print(f"Falhas: {falhas}")

    if falhas == 0:
        print("\nFinalizado. Agora atualize/reinicie o app e confira a Loja.")
    else:
        print("\nFinalizado com falhas. Me envie o log acima para eu ajustar.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERRO GERAL: {e}")
        sys.exit(1)
