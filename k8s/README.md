# Kubernetes

Pour la pré-production et la production, les stacks sont déployée sur des clusters Kubernetes.
La configuration de Kubernetes est déclarative, c'est à dire que l'on déclare ce que l'on veut dans des fichiers YAML et on demande au cluster de l'appliquer.
Ainsi, toute la configuration peut être stockée dans le repo et lorsque l'on met à jours les fichiers, c'est appliqué sur le cluster via le CD.

Ce dossier contient toute la configuration nécessaire des stacks kubernetes.

## kubectl

C'est LA commande qui permet de que communiquer avec le cluster. Avec cette commande on peut lister les objets kubernetes, en créer, en supprimer, etc.

## Namespace

On définit un namespace par instance QxSMS. Il est nommé de la forme qxsms-<instance>. Le namespace regroupe tous les objets de l'instance concernée (pods, pvc, ingress, services).
Le namespace est définit dans le fichier k8s/overlays/<environnement>/<instance>/ns.yml.
Ensuite on spécifiera à tous les autres objets qu'on va créer de le faire dans ce namespace via le fichier k8s/overlays/<environnement>/<instance>/kustomization.yml via le champ namespace.

Ca s'applique avec la commande:

```
kubectl apply -f k8s/overlays/<environment>/<instance>/namespace.yml
```

## Kustomize

Pour organiser la configuration et gérer le multi-environnement (dev,staging,prod), on utilise l'outil [Kustomize](https://kustomize.io/) qui est maintenant intégré nativement à kubectl.

### Base

Le fonctionnement de kustomize est de définir une base commune à tous les déploiemnts, par exemple ils ont tous besoin d'une BDD, un rabbit, l'application, de volumes et de "services" pour pouvoir être contactés.
Ceci est dans le dossier `base`, ensuite il y a un dossier par service et le fichier `kustomization.yml` qui sera inclus dans les **overlays**.

### Overlays

Les overlays sont des surcouches qu'on applique sur la base pour modifier ou ajouter des valeurs prédéfinies. Ca peut être le tag de l'image docker à utliser, les variables d'environnement, le domaine de l'application. Tout ce que qui peut différer d'un environnement à l'autre.

Tout se passe dans le dossier `overlays`, et les sous-dossiers sont nommés de la même manière de que les branches git.

Pour ce projet où l'on veut déployer plusieurs instances de la même stack, il ne faut plus voir les overlays comme des stacks directement mais plutôt comme le **cluster K8S ciblé**.
Ainsi, l'overlay "staging" déploie toutes les stacks (les sous dossiers d'instances) sur le cluster kubernetes de pprd et l'overlay "production" sur celui de prod. Et ces déploiements sont déclenchés par des push sur les branches git du même nom, mais on pourrait faire différemment si vous trouvez que ce n'est plus adapté.

Chaque dossier contient d'autres yaml à appliquer comme les ingress (reverse proxy kubernetes) où l'on définit le domaine, ou les variables d'environnement à utiliser pour ce contexte (pas de DEBUG en prod, adresses mail différentes,etc.)

Enfin le fichier `kustomization.yml` qui inclut le `kustomization.yml` de la base, et les yaml de l'overlay, génère les Docker secrets et spécifie quel tag d'image utiliser, quel namespace utiliser, etc.

Kustomize permet aussi de définir à un seul endroit des informations commune à tous les déploiements, par exemple un préfixe, ou des labels.

Pour déployer une configuration avec kustomize on utilise la commande:

```
kubectl apply -k k8s/overlays/<environnement>/<instance>
```

Exemple pour le dev:
```
kubectl apply -k k8s/overlays/staging/pprd
```
(On note le `-k` et pas le `-f` pour bien spéficier que c'est de la configuration kustomize)

Note: L'overlay `development` n'est pas déployé sur un vrai cluster par le CD, il est là pour tester des configurations k8s en local avant de les modifier sur les vrais déploiements, avec [minikube](https://kubernetes.io/docs/tasks/tools/install-minikube/) par exemple. C'est globalement l'équivalent du `docker-compose.yml` mais au format kubernetes.


# Gitlab CI

Un fichier `.gitlab.ci.yml` permet d'appliquer la configuration kubernetes via le stage `deploy.

Lors d'un push sur la branche `staging`, les instances de l'overlay `staging` (dossier `k8s/overlays/staging`) sont appliquées.

Lors d'un push sur la branche `production`, les instances de l'overlay `production` (dossier `k8s/overlays/production`) sont appliquées.


Si les fichiers n'ont pas été modifiés et qu'une pipeline passe, rien ne sera appliqué sur les clusters kubernetes.

Si la configuration a été modifiée à la main sur les clusters kubernetes et qu'une pipeline passe, la configuration sera modifiée par celle du repo.

**Si on modifie la configuration de la `base`, la modification sera appliquée à toutes les stacks.**


La configuration dans `k8s/overlays/development` est là pour tester et modifier la configuration kubernetes en local avec [minikube](https://kubernetes.io/fr/docs/setup/learning-environment/minikube/).

Le stage `deploy` permet d'appliquer la configuration avec `kubectl` en bouclant sur le dossier des overlays de l'environnement concerné.


Pour chaque cluster kubernetes configuré dans Gitlab, il correspond à un scope (`staging` ou `production`). Lorsque que la pipeline est lancée dans ce scope, les variables d'environnements de la pipeline contienne les informations de connexion au cluster visé.

# Rajouter une stack

Copier un des dossier d'instance dans le dossier de l'environment désiré  (`k8s/overlays/staging` ou `k8s/overlays/production`):

```bash
cp -r k8s/overlays/staging/pprd k8s/overlays/staging/manouvelleinstance
```

Puis modifier le contenu en fonction de ses besoins (variables d'environment, URI dans l'ingress, namespace):

```bash
vi k8s/overlays/staging/manouvelleinstance/namespace.yml
vi k8s/overlays/staging/manouvelleinstance/ingress.yml
vi k8s/overlays/staging/manouvelleinstance/env.yml
vi k8s/overlays/staging/manouvelleinstance/pvc.yml
vi k8s/overlays/staging/manouvelleinstance/kustomization.yml
```

Et enfin commiter et pusher les modification dans la branch du cluster concerné (`staging` ou `production`):

```
(master) $ git add k8s/overlays/staging/manouvelleinstance/
(master) $ git commit -m "Ajout de l'instance manouvelleinstance"
(master) $ git push
(staging) $ git checkout staging
(staging) $ git merge master
(staging) $ git push
```

# Mettra à jour les images des conteneurs sans modifier la configuration

Parfois on peut vouloir mettre à jour les images déjà déployée par des nouvelles images fraichement buildées.

Sauf que si on fait passer la pipeline sans modifier les fichiers de configuration (même tag d'image par exemple), les images ne vont pas être redéployées.

Pour le faire, on peut utiliser la commande [rollout]() de `kubectl`:

```bash
kubectl -n qxsms-<instance> rollout restart deployment qxsms
kubectl -n qxsms-<instance> rollout restart deployment worker
```

# Supprimer une stack

Pour supprimer une stack, rien n'est automatisé pour éviter des erreurs. Il vaut mieux que ça vienne d'une volonté ferme en tapant une commande pour ça.

Une fois le CLI  `kubectl` configuré pour contacter les clusters, on peut supprimer une stack avec une seule commande:

```
kubectl delete -k k8s/overlays/<environnement>/<instance>
```

Exemple pour la pprd (`.kube/config` qui pointe vers le cluster `cdsp-pprd`):
```
kubectl delete -k k8s/overlays/staging/pprd
```

Si on n'aime pas la CLI, on peut aussi supprimer le namespace correspondant via l'interface Web Rancher: Cliquer sur le nom du cluster puis onglet `Projects/Namespaces`
Puis supprimer le namespace et ça supprimera le déploiement ses objets hérités.

** A savoir que par sécurité les volumes ne sont pas supprimés à la suite de ça. **

## Recupérer les données des Volumes

Le plus simple c'est quand la stack tourne encore,  on peut faire des copies avec `kubectl cp`

Si le dépoiement est déjà supprimé, on peut aller chercher les données sur le serveur NFS directement.
Pour la deuxième solution, noter le nom des PVC concernés:
```
kubectl -n qxsms-pprd get pvc
```
Le nom du dossier sur le serveur sera la colonne "VOLUME".

Ensuite on peut récupérer les dossiers via `scp` ou `rsync` sur le serveur NFS, il sont dans le dossier `/srv/nfs`.
Serveur de PPRD: `k8s-nfs-pprd-01.cdsp.sciences-po.fr`
Serveur de PROD: `k8s-nfs-prod-01.cdsp.sciences-po.fr`

Exemple:
```
rsync -a jri@k8s-nfs-pprd-01.cdsp.sciences-po.fr:/srv/nfs/pvc-93846930-e8f4-470d-baf9-b7673f999ea2 /dossier/local
```
## Supprimer définitivement les volumes

Si on veut supprimer aussi les volumes il faudra le faire manuellement via les commanndes `kubectl`.
Pour avoir la liste des volumes persistants:
```
kubectl get pv
```
Cherchez les volumes en status "Released" qui nous concernent (s'aider de la colonne CLAIM).
Puis supprimer les volumes:
```
kubectl delete pv <nom-pv>
```
Exemple:
```
kubectl delete pv pvc-e113f7fb-8800-4c52-bbcb-5987c1e9b4a7
```
Si on n'aime pas la CLI, on peut aussi supprimer le namespace correspondant via l'interface Web Rancher: Cliquer sur le nom du cluster puis onglet `Storage` > `Persistent Volumes`.
Puis supprimer les volumes en état "Released" qui nous concernent.

** Une fois la stack supprimée on peut enlever le dossier la concernant dans les overlays du repo pour éviter qu'elle soit redéployée à la prochaine pipeline.**
