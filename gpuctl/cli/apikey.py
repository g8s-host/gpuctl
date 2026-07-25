"""`gpuctl apikey` 子命令：create / list / revoke。

直连 K8s Secret（不走 HTTP API），因此在 GPUCTL_API_AUTH=apikey 且还没有任何
key 的冷启动场景下也能创建第一把 key。需要当前 kubeconfig 有 Secret 读写权限。
"""
from gpuctl.apikeys import ApiKeyStore, KNOWN_SCOPES


def create_apikey_command(args):
    store = ApiKeyStore()
    scopes = [s.strip() for s in (args.scopes or "").split(",") if s.strip()]
    try:
        token, info = store.create(
            name=args.name, scopes=scopes,
            namespace=args.bind_namespace or "*",
            expires_days=args.expires_days,
        )
    except ValueError as e:
        print(f"Error: {e}")
        print(f"Known scopes: {', '.join(sorted(KNOWN_SCOPES))}")
        raise SystemExit(1)
    print(f"API key created (key_id={info.key_id}, secrets namespace={store.namespace})")
    print()
    print(f"  {token}")
    print()
    print("Store it now — the plaintext key is shown only once.")


def list_apikeys_command(args):
    store = ApiKeyStore()
    infos = store.list()
    if not infos:
        print("No API keys.")
        return
    fmt = "{:<18} {:<20} {:<10} {:<12} {:<26} {}"
    print(fmt.format("KEY_ID", "NAME", "HINT", "NAMESPACE", "CREATED", "SCOPES"))
    for i in infos:
        print(fmt.format(i.key_id, i.name, i.hint, i.namespace,
                         i.created_at[:19], ",".join(i.scopes)))


def revoke_apikey_command(args):
    store = ApiKeyStore()
    if store.revoke(args.key_id):
        print(f"API key {args.key_id} revoked.")
    else:
        print(f"Error: API key {args.key_id} not found.")
        raise SystemExit(1)
