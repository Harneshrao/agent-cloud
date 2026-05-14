# Route matrix: `agent_cloud.app.api.main:app`

| Method | Path | Endpoint name | Tags | Dependency hints |
|--------|------|-----------------|------|------------------|
| GET | `/docs` | swagger_ui_html |  |  |
| GET | `/docs/oauth2-redirect` | swagger_ui_redirect |  |  |
| GET | `/health` | <lambda> |  | <lambda> |
| GET | `/openapi.json` | openapi |  |  |
| GET | `/redoc` | redoc_html |  |  |
| POST | `/v1/agents/publish` | agents_publish | agents,marketplace | agents_publish;get_current_user_optional |
| POST | `/v1/agents/run` | agents_run | agents,marketplace | agents_run;require_project_context;get_current_user;require_project_id |
| GET | `/v1/agents/store` | agents_store | agents,marketplace | agents_store |
| GET | `/v1/agents/{name}/latest` | agents_latest | agents,marketplace | agents_latest |
| POST | `/v1/auth/login` | login | auth,auth | login |
| GET | `/v1/auth/me` | me | auth,auth | me;get_current_user |
| POST | `/v1/auth/register` | register | auth,auth | register |
| GET | `/v1/system/version` | version | system | version |
| POST | `/v1/tasks/enqueue` | enqueue_task | tasks | enqueue_task;get_task_service |
| GET | `/v1/tasks/{task_id}` | get_task_stub | tasks | get_task_stub |
| GET | `/v1/workflows/analytics/aggregate` | get_workflow_aggregate_analytics | workflows,workflows | get_workflow_aggregate_analytics;require_project_context;get_current_user;require_project_id |
| GET | `/v1/workflows/analytics/run/{workflow_id}` | get_workflow_run_analytics | workflows,workflows | get_workflow_run_analytics;require_project_context;get_current_user;require_project_id |
| POST | `/v1/workflows/demo` | post_demo_workflow | workflows,workflows | post_demo_workflow;require_project_can_run;require_project_context;get_current_user;require_project_id |
| POST | `/v1/workflows/optimization/apply` | post_workflow_optimization_apply | workflows,workflows | post_workflow_optimization_apply;require_project_context;get_current_user;require_project_id |
| GET | `/v1/workflows/optimization/recommendations` | get_workflow_recommendations | workflows,workflows | get_workflow_recommendations;require_project_context;get_current_user;require_project_id |
| GET | `/v1/workflows/optimization/slow-nodes` | get_workflow_slow_nodes | workflows,workflows | get_workflow_slow_nodes;require_project_context;get_current_user;require_project_id |
| GET | `/v1/workflows/optimization/summary` | get_workflow_optimization_summary | workflows,workflows | get_workflow_optimization_summary;require_project_context;get_current_user;require_project_id |
| GET | `/v1/workflows/{task_id}` | get_workflow | workflows,workflows | get_workflow;require_project_context;get_current_user;require_project_id |
| POST | `/v1/workflows/{workflow_id}/resume` | post_workflow_resume | workflows,workflows | post_workflow_resume;require_project_context;get_current_user;require_project_id |

_Total routes: 24_
