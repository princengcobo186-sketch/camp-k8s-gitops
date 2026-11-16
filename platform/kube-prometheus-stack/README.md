# kube-prometheus-stack (dev)

Metrics and Grafana for the dev cluster. Argo CD syncs the chart; the admin login is created
out of band so the password never enters git.

## One-time, before the first sync

Point kubectl at the dev cluster, using the `camp-dev` alias from `aws eks update-kubeconfig`:

```sh
aws eks update-kubeconfig --name camp-dev --alias camp-dev --region eu-north-1
```

The `monitoring` namespace must exist and hold the Grafana admin Secret. Create the namespace,
then the Secret, then let Argo sync:

```sh
kubectl --context camp-dev -n monitoring create namespace monitoring --dry-run=client -o yaml | kubectl --context camp-dev apply -f -
kubectl --context camp-dev -n monitoring create secret generic grafana-admin \
  --from-literal=admin-user=admin \
  --from-literal=admin-password="$(openssl rand -base64 24)"
```

Without the Secret, Grafana's pod waits in `CreateContainerConfigError`; the rest of the stack
still syncs.

## Reach Grafana

Grafana is not exposed on a load balancer. Use a port-forward:

```sh
kubectl --context camp-dev -n monitoring port-forward svc/kube-prometheus-stack-grafana 3000:80
```

Then open http://localhost:3000 and sign in as `admin` with the password from the Secret:

```sh
kubectl --context camp-dev -n monitoring get secret grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d
```

## Rotate the password

Replace the Secret's value, then restart Grafana: `kubectl -n monitoring rollout restart deploy/kube-prometheus-stack-grafana`.
