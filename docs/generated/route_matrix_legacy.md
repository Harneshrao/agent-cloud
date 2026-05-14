# Route matrix: `api.main:app`

| Method | Path | Endpoint name | Tags | Dependency hints |
|--------|------|-----------------|------|------------------|
| GET | `/` | root |  | root |
| GET | `/agent-instances` | get_instances | agent-instances | get_instances;require_project_context;get_current_user;require_project_id |
| POST | `/agent-instances` | post_create_instance | agent-instances | post_create_instance;require_project_context;get_current_user;require_project_id |
| GET | `/agent-instances/{instance_id}` | get_instance_by_id | agent-instances | get_instance_by_id;require_project_context;get_current_user;require_project_id |
| POST | `/agent-instances/{instance_id}/autonomous-cycle` | post_instance_autonomous_cycle | agent-instances | post_instance_autonomous_cycle;require_project_context;get_current_user;require_project_id |
| POST | `/agent-instances/{instance_id}/run` | post_instance_run | agent-instances | post_instance_run;require_project_context;get_current_user;require_project_id |
| PATCH | `/agent-instances/{instance_id}/state` | patch_instance_state | agent-instances | patch_instance_state;require_project_context;get_current_user;require_project_id |
| POST | `/agent/run` | agent_run_alias | marketplace | agent_run_alias;require_project_context;get_current_user;require_project_id |
| GET | `/agents` | list_agents |  | list_agents |
| GET | `/agents/installations` | list_installations | agents-installations | list_installations;require_project_context;get_current_user;require_project_id |
| POST | `/agents/installations` | install | agents-installations | install;require_project_context;get_current_user;require_project_id |
| PATCH | `/agents/installations/schedules/{schedule_id}` | update_schedule | agents-installations | update_schedule;require_project_context;get_current_user;require_project_id |
| GET | `/agents/installations/{installation_id}` | get_installation_detail | agents-installations | get_installation_detail;require_project_context;get_current_user;require_project_id |
| PATCH | `/agents/installations/{installation_id}/configuration` | update_configuration | agents-installations | update_configuration;require_project_context;get_current_user;require_project_id |
| POST | `/agents/installations/{installation_id}/run` | run_agent | agents-installations | run_agent;require_project_context;get_current_user;require_project_id |
| GET | `/agents/installations/{installation_id}/runs` | list_runs | agents-installations | list_runs;require_project_context;get_current_user;require_project_id |
| GET | `/agents/installations/{installation_id}/schedules` | list_schedules_for_installation | agents-installations | list_schedules_for_installation;require_project_context;get_current_user;require_project_id |
| POST | `/agents/installations/{installation_id}/schedules` | create_schedule_for_installation | agents-installations | create_schedule_for_installation;require_project_context;get_current_user;require_project_id |
| POST | `/agents/publish` | agents_publish | marketplace | agents_publish;get_current_user_optional |
| POST | `/agents/register` | register_agent |  | register_agent |
| POST | `/agents/run` | agents_run | marketplace | agents_run;require_project_context;get_current_user;require_project_id |
| GET | `/agents/store` | agents_store | marketplace | agents_store |
| GET | `/agents/top` | agents_top | marketplace-ecosystem | agents_top |
| GET | `/agents/trending` | agents_trending | marketplace-ecosystem | agents_trending |
| POST | `/agents/v2/run` | run_v2_agent | agents-v2 | run_v2_agent;require_project_can_run;require_project_context;get_current_user;require_project_id |
| GET | `/agents/{name}/latest` | agents_latest | marketplace | agents_latest |
| POST | `/agents/{name}/rate` | agents_rate | marketplace-ecosystem | agents_rate;require_project_context;get_current_user;require_project_id |
| GET | `/agents/{name}/ratings` | agents_ratings | marketplace-ecosystem | agents_ratings |
| GET | `/api-keys` | get_api_keys | api-keys | get_api_keys;get_current_user |
| POST | `/api-keys` | post_create_key | api-keys | post_create_key;get_current_user |
| DELETE | `/api-keys/{key_id}` | delete_api_key | api-keys | delete_api_key;get_current_user |
| GET | `/autonomous/policies` | list_policies | autonomous-policies | list_policies;require_project_context;get_current_user;require_project_id |
| POST | `/autonomous/policies` | post_set_policy | autonomous-policies | post_set_policy;require_project_context;get_current_user;require_project_id |
| GET | `/autonomous/policies/{agent_name}` | get_agent_policy | autonomous-policies | get_agent_policy;require_project_context;get_current_user;require_project_id |
| GET | `/dashboard` | get_dashboard | dashboard | get_dashboard;require_project_context;get_current_user;require_project_id |
| POST | `/demo/run` | post_demo_run | demo | post_demo_run;require_project_can_run;require_project_context;get_current_user;require_project_id |
| GET | `/developers/agents` | developers_agents | developers | developers_agents |
| POST | `/developers/agents` | post_publish_agent | developer-economy | post_publish_agent;get_current_user |
| POST | `/developers/agents/publish` | post_publish_agent_with_package | developer-economy | post_publish_agent_with_package;get_current_user |
| GET | `/developers/agents/{agent_id}/fraud-signals` | get_agent_fraud_signals | developer-economy | get_agent_fraud_signals;require_admin;get_current_user |
| GET | `/developers/agents/{agent_id}/sandbox` | get_agent_sandbox | developer-economy | get_agent_sandbox;get_current_user |
| PUT | `/developers/agents/{agent_id}/sandbox` | put_agent_sandbox | developer-economy | put_agent_sandbox;get_current_user |
| POST | `/developers/agents/{agent_id}/submit-review` | post_submit_for_review | developer-economy | post_submit_for_review;get_current_user |
| GET | `/developers/agents/{agent_id}/trust` | get_agent_trust | developer-economy | get_agent_trust;get_current_user |
| POST | `/developers/agents/{agent_id}/upload` | post_agent_upload | developer-economy | post_agent_upload;get_current_user |
| GET | `/developers/agents/{agent_id}/verification` | get_agent_verification | developer-economy | get_agent_verification;get_current_user |
| PUT | `/developers/agents/{agent_id}/verification` | put_agent_verification | developer-economy | put_agent_verification;require_admin;get_current_user |
| POST | `/developers/agents/{agent_id}/versions` | post_agent_version | developer-economy | post_agent_version;get_current_user |
| GET | `/developers/agents/{agent_name}/stats` | developers_agent_stats | developers | developers_agent_stats;get_current_user |
| GET | `/developers/dashboard` | developers_dashboard | developers | developers_dashboard;get_current_user |
| GET | `/developers/dashboard` | get_dashboard | developer-economy | get_dashboard;get_current_user |
| GET | `/developers/earnings` | get_earnings | developer-economy | get_earnings;get_current_user |
| GET | `/developers/my-agents` | get_my_agents | developer-economy | get_my_agents;get_current_user |
| GET | `/developers/payouts` | get_payouts | developer-economy | get_payouts;get_current_user |
| GET | `/developers/profile` | get_my_profile | developer-economy | get_my_profile;get_current_user |
| POST | `/developers/register` | post_register | developer-economy | post_register;get_current_user |
| GET | `/developers/revenue` | developers_revenue | developers | developers_revenue;get_current_user |
| GET | `/docs` | swagger_ui_html |  |  |
| GET | `/docs/oauth2-redirect` | swagger_ui_redirect |  |  |
| POST | `/events` | ingest_event | events | ingest_event;require_project_context;get_current_user;require_project_id |
| GET | `/events/triggers` | list_triggers | events | list_triggers;require_project_context;get_current_user;require_project_id |
| POST | `/events/triggers` | create_trigger | events | create_trigger;require_project_context;get_current_user;require_project_id |
| DELETE | `/events/triggers/{trigger_id}` | disable_trigger | events | disable_trigger;require_project_context;get_current_user;require_project_id |
| GET | `/health` | health |  | health |
| POST | `/login` | login | auth | login |
| GET | `/marketplace/agents` | list_marketplace_agents | marketplace | list_marketplace_agents |
| GET | `/marketplace/recommendations` | get_recommendations | marketplace | get_recommendations |
| GET | `/marketplace/search` | search_marketplace | marketplace | search_marketplace |
| GET | `/me` | me | auth | me;get_current_user |
| GET | `/openapi.json` | openapi |  |  |
| GET | `/packages` | list_packages | packages | list_packages |
| GET | `/packages/marketplace` | packages_marketplace | packages | packages_marketplace |
| GET | `/packages/trending` | packages_trending | packages | packages_trending |
| GET | `/packages/{name}` | get_package | packages | get_package |
| POST | `/packages/{name}/install` | install_package_endpoint | packages | install_package_endpoint;get_current_user |
| GET | `/plans` | get_plans | plans | get_plans;get_current_user |
| GET | `/projects` | list_projects | projects | list_projects;get_current_user |
| POST | `/projects` | create_project | projects | create_project;get_current_user |
| GET | `/projects/{project_id}/templates` | list_project_templates | projects | list_project_templates;get_current_user |
| GET | `/redoc` | redoc_html |  |  |
| POST | `/register` | register | auth | register |
| GET | `/schedule` | list_schedules | scheduler | list_schedules;require_project_context;get_current_user;require_project_id |
| POST | `/schedule` | create_schedule | scheduler | create_schedule;require_project_context;get_current_user;require_project_id |
| DELETE | `/schedule/{schedule_id}` | disable_schedule | scheduler | disable_schedule;require_project_context;get_current_user;require_project_id |
| GET | `/scheduler/task` | scheduler_get_task | task-scheduler | scheduler_get_task |
| PATCH | `/schedules/{schedule_id}` | patch_schedule | schedules | patch_schedule;require_project_context;get_current_user;require_project_id |
| GET | `/simulations` | list_runs | simulations | list_runs;require_project_context;get_current_user;require_project_id |
| POST | `/simulations` | create | simulations | create;require_project_context;get_current_user;require_project_id |
| GET | `/simulations/{simulation_id}` | get_run | simulations | get_run;require_project_context;get_current_user;require_project_id |
| GET | `/simulations/{simulation_id}/events` | list_events | simulations | list_events;require_project_context;get_current_user;require_project_id |
| POST | `/simulations/{simulation_id}/events` | inject | simulations | inject;require_project_context;get_current_user;require_project_id |
| POST | `/simulations/{simulation_id}/process-events` | process_events | simulations | process_events;require_project_context;get_current_user;require_project_id |
| POST | `/simulations/{simulation_id}/start` | start | simulations | start;require_project_context;get_current_user;require_project_id |
| GET | `/system/alerts` | get_system_alerts | system | get_system_alerts |
| GET | `/system/autoscaler` | get_system_autoscaler | system | get_system_autoscaler;require_admin;get_current_user |
| GET | `/system/containers` | get_system_containers | system | get_system_containers;require_admin;get_current_user |
| GET | `/system/dead_letters` | get_system_dead_letters | system | get_system_dead_letters;require_admin;get_current_user |
| GET | `/system/health` | get_system_health | system | get_system_health;require_admin;get_current_user |
| GET | `/system/health` | get_system_health | system | get_system_health;require_admin;get_current_user |
| GET | `/system/metrics` | get_system_metrics | system | get_system_metrics;require_admin;get_current_user |
| GET | `/system/queue` | get_system_queue | system | get_system_queue;require_admin;get_current_user |
| GET | `/system/recovery` | get_system_recovery | system | get_system_recovery;require_admin;get_current_user |
| GET | `/system/workers` | get_system_workers | system | get_system_workers;require_admin;get_current_user |
| GET | `/teams` | list_teams | teams | list_teams;get_current_user |
| POST | `/teams` | create_team | teams | create_team;get_current_user |
| GET | `/templates` | get_templates | templates | get_templates |
| POST | `/templates` | post_templates | templates | post_templates;get_current_user |
| GET | `/templates/marketplace` | templates_marketplace | templates | templates_marketplace |
| GET | `/templates/public` | templates_public | templates | templates_public |
| GET | `/templates/top` | templates_top | templates | templates_top |
| GET | `/templates/trending` | templates_trending | templates | templates_trending |
| GET | `/templates/{template_id}` | get_template | templates | get_template |
| POST | `/templates/{template_id}/approve` | post_template_approve | templates | post_template_approve;get_current_user |
| POST | `/templates/{template_id}/fork` | post_template_fork | templates | post_template_fork;get_current_user |
| DELETE | `/templates/{template_id}/install` | delete_template_install | templates | delete_template_install;require_project_context;get_current_user;require_project_id |
| POST | `/templates/{template_id}/install` | post_template_install | templates | post_template_install;require_project_context;get_current_user;require_project_id |
| POST | `/templates/{template_id}/publish` | post_template_publish | templates | post_template_publish;get_current_user |
| POST | `/templates/{template_id}/rate` | post_template_rate | templates | post_template_rate;require_project_context;get_current_user;require_project_id |
| GET | `/templates/{template_id}/ratings` | get_template_ratings | templates | get_template_ratings |
| POST | `/templates/{template_id}/run` | post_template_run | templates | post_template_run;require_project_context;get_current_user;require_project_id |
| GET | `/usage` | get_usage | usage | get_usage;require_project_context;get_current_user;require_project_id |
| POST | `/war-room/analyze` | war_room |  | war_room |
| POST | `/webhooks/{source}` | ingest_webhook | webhooks | ingest_webhook |
| GET | `/workflows/analytics/aggregate` | get_workflow_aggregate_analytics | workflows | get_workflow_aggregate_analytics;require_project_context;get_current_user;require_project_id |
| GET | `/workflows/analytics/run/{workflow_id}` | get_workflow_run_analytics | workflows | get_workflow_run_analytics;require_project_context;get_current_user;require_project_id |
| POST | `/workflows/demo` | post_demo_workflow | workflows | post_demo_workflow;require_project_can_run;require_project_context;get_current_user;require_project_id |
| POST | `/workflows/optimization/apply` | post_workflow_optimization_apply | workflows | post_workflow_optimization_apply;require_project_context;get_current_user;require_project_id |
| GET | `/workflows/optimization/recommendations` | get_workflow_recommendations | workflows | get_workflow_recommendations;require_project_context;get_current_user;require_project_id |
| GET | `/workflows/optimization/slow-nodes` | get_workflow_slow_nodes | workflows | get_workflow_slow_nodes;require_project_context;get_current_user;require_project_id |
| GET | `/workflows/optimization/summary` | get_workflow_optimization_summary | workflows | get_workflow_optimization_summary;require_project_context;get_current_user;require_project_id |
| GET | `/workflows/{task_id}` | get_workflow | workflows | get_workflow;require_project_context;get_current_user;require_project_id |
| POST | `/workflows/{workflow_id}/resume` | post_workflow_resume | workflows | post_workflow_resume;require_project_context;get_current_user;require_project_id |

_Total routes: 132_
