-- GarageHub App Bridge
-- Execute APÓS a importação Base44 -> garagehub_*.
-- Este script cria as tabelas que o app.py atual espera e popula com os dados importados.

create table if not exists public.usuarios (
    id bigserial primary key,
    base44_id text unique,
    nome text not null,
    email text unique,
    senha text not null default '123456',
    tipo text default 'usuario',
    status text default 'ativo',
    codigo_membro text,
    telefone text,
    cidade text,
    estado text,
    instagram text,
    foto_perfil_url text,
    nivel_cliente text default 'comum',
    criado_em timestamptz default now()
);

create table if not exists public.minis (
    id bigserial primary key,
    base44_id text unique,
    usuario_id bigint references public.usuarios(id) on delete set null,
    nome text not null,
    marca text,
    serie text,
    ano text,
    raridade text default 'Comum',
    valor_pago numeric(12,2) default 0,
    valor_estimado numeric(12,2) default 0,
    foto_url text,
    status_pagamento text default 'pendente',
    tipo_mini text default 'compra',
    destaque_cliente text,
    criado_em timestamptz default now()
);

create table if not exists public.loja_minis (
    id bigserial primary key,
    base44_id text unique,
    nome text not null,
    marca text,
    serie text,
    ano text,
    raridade text default 'Comum',
    valor numeric(12,2) default 0,
    valor_estimado numeric(12,2) default 0,
    foto_url text,
    status text default 'disponivel',
    destaque text,
    criado_em timestamptz default now()
);

create table if not exists public.pedidos (
    id bigserial primary key,
    base44_id text unique,
    usuario_id bigint references public.usuarios(id) on delete set null,
    loja_mini_id bigint references public.loja_minis(id) on delete set null,
    nome text,
    marca text,
    serie text,
    ano text,
    raridade text default 'Comum',
    valor numeric(12,2) default 0,
    valor_estimado numeric(12,2) default 0,
    foto_url text,
    status text default 'solicitado',
    observacoes text,
    criado_em timestamptz default now()
);

-- Admin inicial para você entrar no app.
-- Login: admin@garagehub.com / Senha: 123456
insert into public.usuarios (nome, email, senha, tipo, status, codigo_membro, nivel_cliente)
values ('Admin GarageHub', 'admin@garagehub.com', '123456', 'admin', 'ativo', 'GHW-ADMIN', 'vip')
on conflict (email) do update set tipo='admin', status='ativo', nivel_cliente='vip';

-- Clientes importados da Base44 viram usuários do app.
-- Senha padrão: últimos 4 dígitos do telefone. Se não tiver telefone, usa 123456.
insert into public.usuarios (
    base44_id, nome, email, senha, tipo, status, codigo_membro,
    telefone, cidade, estado, foto_perfil_url, nivel_cliente, criado_em
)
select
    c.base44_id,
    coalesce(nullif(c.nome,''), 'Cliente Base44') as nome,
    nullif(c.email,''),
    coalesce(nullif(right(regexp_replace(coalesce(c.telefone,''), '\\D', '', 'g'), 4), ''), '123456') as senha,
    'usuario',
    'ativo',
    concat('GHW-', coalesce(c.id::text, c.base44_id)),
    c.telefone,
    c.cidade,
    c.estado,
    c.foto_url,
    'comum',
    coalesce(c.created_date, now())
from public.garagehub_clientes c
where c.base44_id is not null
on conflict (base44_id) do update set
    nome = excluded.nome,
    telefone = excluded.telefone,
    cidade = excluded.cidade,
    estado = excluded.estado,
    foto_perfil_url = excluded.foto_perfil_url;

-- Produtos vinculados a clientes viram minis nas garagens dos clientes.
insert into public.minis (
    base44_id, usuario_id, nome, marca, serie, ano, raridade,
    valor_pago, valor_estimado, foto_url, status_pagamento, tipo_mini, destaque_cliente, criado_em
)
select
    p.base44_id,
    u.id,
    p.carro,
    coalesce(p.fornecedor, 'Hot Wheels'),
    '',
    '',
    'Comum',
    coalesce(p.preco, 0),
    coalesce(p.preco, 0),
    p.foto_url,
    lower(coalesce(p.pagamento, p.status, 'pendente')),
    'base44_produto',
    coalesce(p.rastreio_url, ''),
    coalesce(p.created_date, now())
from public.garagehub_produtos p
left join public.usuarios u on u.base44_id = p.cliente_base44_id
where p.base44_id is not null and p.carro is not null
on conflict (base44_id) do update set
    usuario_id = excluded.usuario_id,
    nome = excluded.nome,
    marca = excluded.marca,
    valor_pago = excluded.valor_pago,
    valor_estimado = excluded.valor_estimado,
    foto_url = excluded.foto_url,
    status_pagamento = excluded.status_pagamento,
    destaque_cliente = excluded.destaque_cliente;

-- Estoque Base44 vira vitrine/loja.
insert into public.loja_minis (
    base44_id, nome, marca, serie, ano, raridade, valor, valor_estimado, foto_url, status, destaque, criado_em
)
select
    e.base44_id,
    e.carro,
    coalesce(e.fornecedor, 'Hot Wheels'),
    coalesce(e.categoria, ''),
    '',
    'Comum',
    coalesce(e.preco, 0),
    coalesce(e.preco, 0),
    e.foto_url,
    case when coalesce(e.quantidade, 1) > 0 then 'disponivel' else 'vendido' end,
    concat('Qtd: ', coalesce(e.quantidade, 1)::text),
    coalesce(e.created_date, now())
from public.garagehub_estoque e
where e.base44_id is not null and e.carro is not null
on conflict (base44_id) do update set
    nome = excluded.nome,
    marca = excluded.marca,
    serie = excluded.serie,
    valor = excluded.valor,
    valor_estimado = excluded.valor_estimado,
    foto_url = excluded.foto_url,
    status = excluded.status,
    destaque = excluded.destaque;

-- Pedidos importados entram no módulo de pedidos.
insert into public.pedidos (
    base44_id, usuario_id, nome, marca, serie, ano, raridade, valor, valor_estimado, foto_url, status, observacoes, criado_em
)
select
    p.base44_id,
    u.id,
    coalesce(p.cliente_nome, 'Pedido Base44'),
    'GarageHub',
    '',
    '',
    'Comum',
    coalesce(p.total, 0),
    coalesce(p.total, 0),
    p.comprovante_url,
    lower(coalesce(p.status, 'solicitado')),
    coalesce(p.observacao, ''),
    coalesce(p.created_date, now())
from public.garagehub_pedidos p
left join public.usuarios u on u.base44_id = p.cliente_base44_id
where p.base44_id is not null
on conflict (base44_id) do update set
    usuario_id = excluded.usuario_id,
    valor = excluded.valor,
    valor_estimado = excluded.valor_estimado,
    status = excluded.status,
    observacoes = excluded.observacoes;

create index if not exists idx_usuarios_email on public.usuarios(email);
create index if not exists idx_minis_usuario_id on public.minis(usuario_id);
create index if not exists idx_loja_minis_status on public.loja_minis(status);
create index if not exists idx_pedidos_usuario_id on public.pedidos(usuario_id);
