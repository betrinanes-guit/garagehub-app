"""
Importador Base44 -> Supabase GarageHub

Como usar:
1) Coloque este arquivo na pasta do projeto GarageHub.
2) Coloque os CSVs exportados da Base44 na mesma pasta ou ajuste CSV_DIR.
3) Instale dependências:
   py -3.12 -m pip install pandas supabase
4) Configure .streamlit/secrets.toml com:
   SUPABASE_URL = "https://tiaxhayiylvqtvwevyfu.supabase.co"
   SUPABASE_KEY = "sb_publishable_0SjaY-hnVXRzsHcyao1nmQ_UaIV5t0d"
5) Execute:
   py -3.12 importar_base44_garagehub.py
"""

from __future__ import annotations

import json
import math
import tomllib
from pathlib import Path
from typing import Any

import pandas as pd
from supabase import create_client

BASE_DIR = Path(__file__).parent
CSV_DIR = BASE_DIR
SECRETS_PATH = BASE_DIR / ".streamlit" / "secrets.toml"

FILES = {
    "clientes": "Cliente_export.csv",
    "produtos": "Produto_export.csv",
    "estoque": "Estoque_export.csv",
    "pedidos": "Pedido_export.csv",
    "configuracao": "Configuracao_export.csv",
    "miniaturas": "Miniatura_export.csv",
}

TABLES = {
    "clientes": "garagehub_clientes",
    "produtos": "garagehub_produtos",
    "estoque": "garagehub_estoque",
    "pedidos": "garagehub_pedidos",
    "configuracao": "garagehub_configuracao",
    "miniaturas": "garagehub_miniaturas",
}


def load_secrets() -> dict[str, str]:
    if not SECRETS_PATH.exists():
        raise FileNotFoundError(
            f"Não encontrei {SECRETS_PATH}. Crie o arquivo com SUPABASE_URL e SUPABASE_KEY."
        )
    data = tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    return {
        "SUPABASE_URL": data["SUPABASE_URL"],
        "SUPABASE_KEY": data["SUPABASE_KEY"],
    }


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def to_bool(value: Any) -> bool | None:
    value = clean_value(value)
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "sim", "yes", "y"}


def to_int(value: Any) -> int | None:
    value = clean_value(value)
    if value is None:
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def to_float(value: Any) -> float | None:
    value = clean_value(value)
    if value is None:
        return None
    try:
        return float(str(value).replace("R$", "").replace(".", "").replace(",", "."))
    except Exception:
        try:
            return float(value)
        except Exception:
            return None


def to_date(value: Any) -> str | None:
    value = clean_value(value)
    if value is None:
        return None
    try:
        return pd.to_datetime(value).date().isoformat()
    except Exception:
        return None


def to_ts(value: Any) -> str | None:
    value = clean_value(value)
    if value is None:
        return None
    try:
        return pd.to_datetime(value, utc=True).isoformat()
    except Exception:
        return None


def to_json(value: Any) -> Any:
    value = clean_value(value)
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return value


def read_csv(name: str) -> pd.DataFrame:
    path = CSV_DIR / name
    if not path.exists():
        print(f"⚠️ Arquivo não encontrado: {name}. Pulando.")
        return pd.DataFrame()
    return pd.read_csv(path)


def upsert_batches(supabase, table: str, rows: list[dict[str, Any]], batch_size: int = 100) -> None:
    if not rows:
        print(f"⚠️ Sem registros para {table}")
        return
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        supabase.table(table).upsert(batch, on_conflict="base44_id").execute()
    print(f"✅ {table}: {len(rows)} registros importados/atualizados")


def map_clientes(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "base44_id": clean_value(r.get("id")),
            "nome": clean_value(r.get("nome")),
            "email": clean_value(r.get("email")),
            "telefone": clean_value(r.get("telefone")),
            "cpf": clean_value(r.get("cpf")),
            "cep": clean_value(r.get("cep")),
            "endereco": clean_value(r.get("endereco")),
            "numero": clean_value(r.get("numero")),
            "complemento": clean_value(r.get("complemento")),
            "bairro": clean_value(r.get("bairro")),
            "cidade": clean_value(r.get("cidade")),
            "estado": clean_value(r.get("estado")),
            "foto_url": clean_value(r.get("foto_url")),
            "rastreio_geral": clean_value(r.get("rastreio_geral")),
            "created_date": to_ts(r.get("created_date")),
            "updated_date": to_ts(r.get("updated_date")),
            "created_by": clean_value(r.get("created_by")),
            "is_sample": to_bool(r.get("is_sample")) or False,
        })
    return rows


def map_produtos(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for _, r in df.iterrows():
        carro = clean_value(r.get("carro"))
        if not carro:
            continue
        rows.append({
            "base44_id": clean_value(r.get("id")),
            "carro": carro,
            "fornecedor": clean_value(r.get("fornecedor")),
            "preco": to_float(r.get("preco")),
            "foto_url": clean_value(r.get("foto_url")),
            "pagamento": clean_value(r.get("pagamento")),
            "cliente_base44_id": clean_value(r.get("cliente_id")),
            "data_vencimento": to_date(r.get("data_vencimento")),
            "rastreio_url": clean_value(r.get("rastreio_url")),
            "status": clean_value(r.get("status")),
            "created_date": to_ts(r.get("created_date")),
            "updated_date": to_ts(r.get("updated_date")),
            "created_by": clean_value(r.get("created_by")),
            "is_sample": to_bool(r.get("is_sample")) or False,
        })
    return rows


def map_estoque(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for _, r in df.iterrows():
        carro = clean_value(r.get("carro"))
        if not carro:
            continue
        rows.append({
            "base44_id": clean_value(r.get("id")),
            "carro": carro,
            "fornecedor": clean_value(r.get("fornecedor")),
            "preco": to_float(r.get("preco")),
            "foto_url": clean_value(r.get("foto_url")),
            "quantidade": to_int(r.get("quantidade")) or 1,
            "categoria": clean_value(r.get("categoria")),
            "created_date": to_ts(r.get("created_date")),
            "updated_date": to_ts(r.get("updated_date")),
            "created_by": clean_value(r.get("created_by")),
            "is_sample": to_bool(r.get("is_sample")) or False,
        })
    return rows


def map_pedidos(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "base44_id": clean_value(r.get("id")),
            "itens": to_json(r.get("itens")),
            "total": to_float(r.get("total")),
            "observacao": clean_value(r.get("observacao")),
            "cliente_nome": clean_value(r.get("cliente_nome")),
            "comprovante_url": clean_value(r.get("comprovante_url")),
            "pagamento_declarado": to_bool(r.get("pagamento_declarado")),
            "cliente_base44_id": clean_value(r.get("cliente_id")),
            "status": clean_value(r.get("status")),
            "created_date": to_ts(r.get("created_date")),
            "updated_date": to_ts(r.get("updated_date")),
            "created_by": clean_value(r.get("created_by")),
            "is_sample": to_bool(r.get("is_sample")) or False,
        })
    return rows


def map_configuracao(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "base44_id": clean_value(r.get("id")),
            "nome_recebedor": clean_value(r.get("nome_recebedor")),
            "chave_pix": clean_value(r.get("chave_pix")),
            "pin_admin": clean_value(r.get("pin_admin")),
            "telefone_admin": clean_value(r.get("telefone_admin")),
            "created_date": to_ts(r.get("created_date")),
            "updated_date": to_ts(r.get("updated_date")),
            "created_by": clean_value(r.get("created_by")),
            "is_sample": to_bool(r.get("is_sample")) or False,
        })
    return rows


def map_miniaturas(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "base44_id": clean_value(r.get("id")),
            "cliente": clean_value(r.get("cliente")),
            "carro": clean_value(r.get("carro")),
            "foto_url": clean_value(r.get("foto_url")),
            "pagamento": clean_value(r.get("pagamento")),
            "status": clean_value(r.get("status")),
            "created_date": to_ts(r.get("created_date")),
            "updated_date": to_ts(r.get("updated_date")),
            "created_by": clean_value(r.get("created_by")),
            "is_sample": to_bool(r.get("is_sample")) or False,
        })
    return rows


def main() -> None:
    secrets = load_secrets()
    supabase = create_client(secrets["SUPABASE_URL"], secrets["SUPABASE_KEY"])

    imports = [
        ("clientes", map_clientes),
        ("produtos", map_produtos),
        ("estoque", map_estoque),
        ("pedidos", map_pedidos),
        ("configuracao", map_configuracao),
        ("miniaturas", map_miniaturas),
    ]

    for key, mapper in imports:
        df = read_csv(FILES[key])
        if df.empty:
            continue
        rows = mapper(df)
        upsert_batches(supabase, TABLES[key], rows)

    print("\n🚀 Migração Base44 -> GarageHub concluída.")


if __name__ == "__main__":
    main()
