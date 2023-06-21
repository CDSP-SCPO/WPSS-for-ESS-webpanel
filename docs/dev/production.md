# Production

CI pipelines defined in `.gitlab-ci.yml` file are started by merges into the protected branches `staging`, `production` and `ovh`.

QxSMS docker image is built by Gitlab CI and pushed to [Gitlab Registry](https://gitlab.sciences-po.fr/cdspit/qxsms/container_registry).

Docker image tags are related to git branch names.

Finally the stack is upgraded via Kubernetes API.

Kubernetes stacks are defined in `k8s` folder using Kustomize tool.
Check [k8s/README.md](k8s/README.md) for more details.

## Getting started with Kubernetes

1. Install `kubectl`, the client to interact with a remote Kubernetes cluster. This will create the `.kube` directory in your `$HOME`.

1. Get the `kubeconfig.yml` file from OVH, and save it as
   `~/.kube/config`

You're all set to interact with the cluster, and here are some handy commands.

List available contexts

```sh
kubectl config get-contexts
```

Restart services to make newly deployed changes effective

```sh
kubectl -n qxsms-wpss rollout restart deployment [worker, qxsms]
```

List all pods

```sh
kubectl get pods
```

Get a shell in a pod

```sh
kubectl exec "$POD_NAME" --container`$CONTAINER --namespace`qxsms-wpss --stdin`true --tty`true -- /bin/sh
```

Get the logs from a pod

```sh
kubectl logs "$POD_NAME" --container`$CONTAINER --namespace`qxsms-wpss --follow`true
```
