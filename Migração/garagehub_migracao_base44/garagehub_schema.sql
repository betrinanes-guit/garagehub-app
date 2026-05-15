-- GarageHub - Schema Supabase separado
-- Execute este arquivo no SQL Editor do Supabase da GarageHub.

create table if not exists public.garagehub_clientes (
    id bigserial primary key,
    base44_id text unique,
    nome text,
    email text,
    telefone text,
    cpf text,
    cep text,
    endereco text,
    numero text,
    complemento text,
    bairro text,
    cidade text,
    estado text,
    foto_url text,
    rastreio_geral text,
    created_date timestamptz,
    updated_date timestamptz,
    created_by text,
    is_sample boolean default false,
    importado_em timestamptz default now()
);

create table if not exists public.garagehub_produtos (
    id bigserial primary key,
    base44_id text unique,
    carro text not null,
    fornecedor text,
    preco numeric(12,2),
    foto_url text,
    pagamento text,
    cliente_base44_id text,
    data_vencimento date,
    rastreio_url text,
    status text,
    created_date timestamptz,
    updated_date timestamptz,
    created_by text,
    is_sample boolean default false,
    importado_em timestamptz default now()
);

create table if not exists public.garagehub_estoque (
    id bigserial primary key,
    base44_id text unique,
    carro text not null,
    fornecedor text,
    preco numeric(12,2),
    foto_url text,
    quantidade integer default 1,
    categoria text,
    created_date timestamptz,
    updated_date timestamptz,
    created_by text,
    is_sample boolean default false,
    importado_em timestamptz default now()
);

create table if not exists public.garagehub_pedidos (
    id bigserial primary key,
    base44_id text unique,
    itens jsonb,
    total numeric(12,2),
    observacao text,
    cliente_nome text,
    comprovante_url text,
    pagamento_declarado boolean,
    cliente_base44_id text,
    status text,
    created_date timestamptz,
    updated_date timestamptz,
    created_by text,
    is_sample boolean default false,
    importado_em timestamptz default now()
);

create table if not exists public.garagehub_configuracao (
    id bigserial primary key,
    base44_id text unique,
    nome_recebedor text,
    chave_pix text,
    pin_admin text,
    telefone_admin text,
    created_date timestamptz,
    updated_date timestamptz,
    created_by text,
    is_sample boolean default false,
    importado_em timestamptz default now()
);

create table if not exists public.garagehub_miniaturas (
    id bigserial primary key,
    base44_id text unique,
    cliente text,
    carro text,
    foto_url text,
    pagamento text,
    status text,
    created_date timestamptz,
    updated_date timestamptz,
    created_by text,
    is_sample boolean default false,
    importado_em timestamptz default now()
);

create index if not exists idx_gh_produtos_carro on public.garagehub_produtos using gin (to_tsvector('portuguese', coalesce(carro,'')));
create index if not exists idx_gh_produtos_status on public.garagehub_produtos(status);
create index if not exists idx_gh_produtos_cliente_base44 on public.garagehub_produtos(cliente_base44_id);
create index if not exists idx_gh_estoque_carro on public.garagehub_estoque using gin (to_tsvector('portuguese', coalesce(carro,'')));
create index if not exists idx_gh_pedidos_cliente_base44 on public.garagehub_pedidos(cliente_base44_id);
