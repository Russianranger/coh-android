-- Run only against the explicitly identified disposable AuthServer account DB.
-- Read-only system metadata. No account rows, procedure bodies, credentials,
-- connection strings, or password hashes are selected. No procedure is run.
-- Requires SQL Server 2016+ FOR JSON support and metadata visibility.
-- Missing metadata/permissions is a refusal, not an inferred empty schema.
SET NOCOUNT ON;
SELECT
  'coh-auth-critical-schema-v1' AS [schema],
  JSON_QUERY((
    SELECT s.name AS [schema], o.name AS [procedure], p.parameter_id AS ordinal,
      t.name AS [type], p.max_length, p.scale,
      CAST(p.is_output AS bit) AS [output], CAST(t.is_user_defined AS bit) AS user_defined
    FROM sys.procedures o
    JOIN sys.schemas s ON s.schema_id = o.schema_id
    JOIN sys.parameters p ON p.object_id = o.object_id
    JOIN sys.types t ON t.user_type_id = p.user_type_id
    WHERE s.name = 'dbo' AND o.name IN ('ap_GPwd', 'ap_GStat', 'get_server_groups')
      AND p.parameter_id > 0
    ORDER BY o.name, p.parameter_id
    FOR JSON PATH
  )) AS parameters,
  JSON_QUERY((
    SELECT s.name AS [schema], o.name AS [table], c.name AS [column],
      t.name AS [type], c.max_length, CAST(t.is_user_defined AS bit) AS user_defined
    FROM sys.tables o
    JOIN sys.schemas s ON s.schema_id = o.schema_id
    JOIN sys.columns c ON c.object_id = o.object_id
    JOIN sys.types t ON t.user_type_id = c.user_type_id
    WHERE s.name = 'dbo' AND (
      (o.name = 'user_auth' AND c.name IN ('account', 'password', 'hash_type', 'salt')) OR
      (o.name = 'user_account' AND c.name IN ('uid', 'account', 'queue_level', 'loyalty_points', 'loyalty_legacy_points')) OR
      (o.name = 'user_data' AND c.name IN ('uid', 'user_data', 'user_data_new', 'user_game_data', 'user_game_data_new')) OR
      (o.name = 'user_server_group' AND c.name IN ('uid', 'server_group_id')) OR
      (o.name = 'server' AND c.name = 'server_group_id')
    )
    ORDER BY o.name, c.name
    FOR JSON PATH
  )) AS columns
FOR JSON PATH, WITHOUT_ARRAY_WRAPPER;
