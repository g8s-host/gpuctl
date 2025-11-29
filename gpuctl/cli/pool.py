from gpuctl.client.pool_client import PoolClient


def get_pools_command(args):
    """获取资源池列表命令"""
    try:
        client = PoolClient()
        pools = client.list_pools()
        
        # 打印资源池列表
        print(f"{'POOL NAME':<30} {'STATUS':<10} {'GPU TOTAL':<10} {'GPU USED':<10} {'GPU FREE':<10} {'GPU TYPE':<15} {'NODE COUNT':<10}")
        print("-" * 120)
        
        for pool in pools:
            print(f"{pool['name']:<30} {pool['status']:<10} {pool['gpu_total']:<10} {pool['gpu_used']:<10} {pool['gpu_free']:<10} {', '.join(pool['gpu_types']):<15} {len(pool['nodes']):<10}")
        
        return 0
    except Exception as e:
        print(f"❌ Error getting pools: {e}")
        return 1


def create_pool_command(args):
    """创建资源池命令"""
    try:
        client = PoolClient()
        
        pool_config = {
            "name": args.name,
            "description": args.description,
            "nodes": args.nodes,
            "gpu_type": args.gpu_type,
            "quota": args.quota
        }
        
        result = client.create_pool(pool_config)
        print(f"✅ Successfully created pool: {result['name']}")
        print(f"📊 Status: {result['status']}")
        print(f"📦 Message: {result['message']}")
        
        return 0
    except Exception as e:
        print(f"❌ Error creating pool: {e}")
        return 1


def delete_pool_command(args):
    """删除资源池命令"""
    try:
        client = PoolClient()
        success = client.delete_pool(args.pool_name)
        
        if success:
            print(f"✅ Successfully deleted pool: {args.pool_name}")
            return 0
        else:
            print(f"❌ Pool not found: {args.pool_name}")
            return 1
    except Exception as e:
        print(f"❌ Error deleting pool: {e}")
        return 1
