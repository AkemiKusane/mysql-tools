SELECT *
    FROM msdb.dbo.sysobjects ,msdb.dbo.sysobjects2
    WHERE (name = N'sp_get_composite_job_info')
        AND (type = 'P');

DROP PROCEDURE sp_get_composite_job_info;

SELECT p.policy_id
        , MAX(h.end_date) execution_date
        , CASE WHEN 0 = COUNT(*) THEN 1 ELSE COUNT(*) END AS evaluation_count
        , p.utilization_type
        , p.health_policy_id
        , p.policy_name
        , pc.occurence_frequency
FROM msdb.dbo.sysutility_ucp_policies as p
INNER JOIN msdb.dbo.syspolicy_policy_execution_history_internal h 
    ON p.policy_id = h.policy_id
INNER JOIN msdb.dbo.sysutility_ucp_policy_configuration pc
    ON p.utilization_type = pc.utilization_type
WHERE h.end_date >= DATEADD(MI, -60*pc.trailing_window, CURRENT_TIMESTAMP) 
    AND h.is_full_run = 1  
    AND p.resource_type = 3 -- Filter volatile resources (currently cpu type only)
GROUP BY p.policy_id
    , p.utilization_type
    , p.health_policy_id
    , p.policy_name
    , pc.occurence_frequency;

CREATE TABLE sysutility_ucp_policy_violations_internal
(
    health_policy_id INT NOT NULL,
    policy_id INT NOT NULL, 
    policy_name SYSNAME NULL,
    history_id INT NOT NULL,
    detail_id INT NOT NULL,
    target_query_expression NVARCHAR(MAX) NULL,
    target_query_expression_with_id NVARCHAR(MAX) NULL,
    execution_date DATETIME NULL,
    result INT NULL,

    CONSTRAINT [PK_sysutility_ucp_policy_violations_internal] 
        PRIMARY KEY CLUSTERED (policy_id, history_id, detail_id)
);

INSERT INTO dbo.sysutility_ucp_policy_violations_internal (p.health_policy_id
    , p.policy_id
    , p.policy_name
    , d.history_id
    , d.detail_id
    , d.target_query_expression
    , d.target_query_expression_with_id
    , d.execution_date
    , d.result) values
SELECT p.health_policy_id
    , p.policy_id
    , p.policy_name
    , d.history_id
    , d.detail_id
    , d.target_query_expression
    , d.target_query_expression_with_id
    , d.execution_date
    , d.result
FROM msdb.dbo.sysutility_ucp_policies p
INNER JOIN msdb.dbo.syspolicy_policy_execution_history_internal h 
    ON h.policy_id = p.policy_id
LEFT JOIN msdb.dbo.syspolicy_policy_execution_history_details_internal d 
    ON d.history_id = h.history_id
WHERE p.resource_type = 1;

SELECT hp.health_policy_id
FROM msdb.dbo.sysutility_ucp_policies hp
WHERE hp.rollup_object_type = @rollup_object_type
    AND hp.target_type = @target_type
    AND hp.resource_type = @resource_type
    AND hp.utilization_type = @utilization_type
    AND hp.is_global_policy = 1
UNION
SELECT hp.health_policy_id
FROM msdb.dbo.sysutility_ucp_policies2 hp
WHERE hp.rollup_object_type = 0
    AND hp.target_type = @target_type
    AND hp.resource_type = @resource_type
    AND hp.utilization_type = @utilization_type
    AND hp.is_global_policy = 1 ;

DELETE FROM msdb.dbo.sysutility_ucp_aggregated_mi_health_internal WHERE set_number < @new_set_number;

UPDATE dbo.sysdac_instances_internal h join hp.health_policy_id on h.policy_id = hp.policy_id
    SET instance_id   = @instance_id, 
        instance_name = @instance_name
    WHERE instance_id = @source_instance_id;