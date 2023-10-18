create table
  public.global_inventory (
    id bigint generated by default as identity,
    num_red_ml integer not null,
    gold integer not null,
    num_blue_ml integer not null,
    num_green_ml integer not null,
    num_dark_ml integer not null,
    constraint global_inventory_pkey primary key (id)
  ) tablespace pg_default;

create table
  public.carts (
    id bigint generated by default as identity,
    customer_name text not null default ''::text,
    constraint carts_pkey primary key (id)
  ) tablespace pg_default;

create table
  public.catalog (
    id bigint generated by default as identity,
    sku text not null,
    name text not null,
    price bigint not null,
    red_ml bigint not null,
    green_ml bigint not null,
    blue_ml bigint not null,
    dark_ml bigint not null,
    stock bigint not null,
    constraint catalog_pkey primary key (id)
  ) tablespace pg_default;

create table
  public.cart_items (
    id bigint generated by default as identity,
    cart_id bigint not null,
    catalog_id bigint not null,
    quantity bigint not null,
    constraint cart_items_pkey primary key (id),
    constraint cart_items_cart_id_fkey foreign key (cart_id) references carts (id) on update cascade on delete cascade,
    constraint cart_items_catalog_id_fkey foreign key (catalog_id) references catalog (id) on update cascade on delete cascade
    constraint cart_items_quantity_check check ((quantity > 0))
  ) tablespace pg_default;

