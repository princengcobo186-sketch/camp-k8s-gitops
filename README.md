# camp-k8s-gitops

The **single source of truth** for what runs in every CAMP cluster. Argo CD in each cluster
watches `clusters/<env>/` and reconciles the cluster to match it (App-of-Apps). Nothing is
applied to a cluster by hand.

| Repository | Owns |
|---|---|
| [camp-infra-live](https://github.com/princengcobo186-sketch/camp-infra-live) | AWS foundations, the Argo CD install and its root Application |
| **camp-k8s-gitops** (this) | Desired cluster state per environment |
| [camp-payment-service](https://github.com/princengcobo186-sketch/camp-payment-service) | Application code, tests, container image, Helm chart |

## How a change reaches a cluster

```
camp-payment-service CI ──► image in ECR (immutable tag)
                         └► PR here: apps/payment-service/envs/dev  image.tag = <sha>
merge ──► Argo CD (dev) syncs
promote = PR copying the same tag to envs/staging, then envs/prod (CODEOWNERS-gated)
rollback = git revert
```

## Layout (populated from Phase 1)

```
clusters/<env>/      root of the App-of-Apps for that cluster
projects/            Argo CD AppProjects: RBAC and blast radius per team
platform/<addon>/    cluster add-ons: pinned chart version + values per env
apps/<app>/envs/     per-environment values; the image tag lives here
```

## Rules

- Images are referenced by immutable tag (git SHA), never `latest`.
- No secrets in this repo. Workloads read them through External Secrets from AWS Secrets Manager.
- One owner per resource: Terraform owns the Argo CD install; this repo owns everything after it.

## Status

Phase 0 (foundations). Plan: [camp-infra-live/docs/platform-plan.md](https://github.com/princengcobo186-sketch/camp-infra-live/blob/main/docs/platform-plan.md).
