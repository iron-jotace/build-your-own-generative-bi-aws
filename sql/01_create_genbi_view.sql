CREATE VIEW nexa_master.vw_nexa_genbi_sales AS
SELECT
  f.sale_id
, f.order_id
, d.full_date sale_date
, d.day_of_month
, d.month_number
, d.quarter_number
, d.year_number
, p.product_id
, p.product_name
, p.category
, p.brand
, p.list_price
, COALESCE(c.customer_id, 'UNIDENTIFIED') customer_id
, COALESCE(c.customer_name, 'Unidentified Customer') customer_name
, COALESCE(c.segment, 'Unidentified') customer_segment
, COALESCE(c.city, 'Not Identified') customer_city
, c.registration_date
, (CASE WHEN (f.customer_key IS NULL) THEN 'Unidentified' ELSE 'Identified' END) customer_identification_status
, COALESCE(s.store_id, 'NO_STORE_ASSIGNED') store_id
, COALESCE(s.store_name, 'No Store Assigned') store_name
, COALESCE(s.city, 'No Store Assigned') store_city
, COALESCE(s.region, 'No Store Assigned') store_region
, (CASE WHEN (f.store_key IS NULL) THEN 'No Store Assigned' ELSE 'Store Assigned' END) store_assignment_status
, ch.channel_name sales_channel
, f.quantity
, f.unit_price
, f.discount
, f.unit_cost
, f.revenue
, f.margin
, ROUND((f.quantity * f.unit_price), 2) gross_sales
, ROUND((f.quantity * f.unit_cost), 2) cost_amount
FROM
  (((((nexa_master.fact_sales f
INNER JOIN nexa_master.dim_product p ON (f.product_key = p.product_key))
LEFT JOIN nexa_master.dim_customer c ON (f.customer_key = c.customer_key))
LEFT JOIN nexa_master.dim_store s ON (f.store_key = s.store_key))
INNER JOIN nexa_master.dim_channel ch ON (f.channel_key = ch.channel_key))
INNER JOIN nexa_master.dim_date d ON (f.date_key = d.date_key))