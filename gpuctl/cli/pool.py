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


def describe_pool_command(args):
    """描述资源池详情命令"""
    try:
        client = PoolClient()
        pool = client.get_pool(args.pool_name)
        
        # 打印资源池详情
        print(f"📋 Pool Details: {args.pool_name}")
        print("=" * 60)
        print(f"📊 Name: {pool.get('name', 'N/A')}")
        print(f"📝 Description: {pool.get('description', 'N/A')}")
        print(f"📈 Status: {pool.get('status', 'unknown')}")
        print(f"🖥️  GPU Total: {pool.get('gpu_total', 'N/A')}")
        print(f"📊 GPU Used: {pool.get('gpu_used', 'N/A')}")
        print(f"🆓 GPU Free: {pool.get('gpu_free', 'N/A')}")
        print(f"🔧 GPU Types: {', '.join(pool.get('gpu_types', []))}")
        print(f"🖥️  Node Count: {len(pool.get('nodes', []))}")
        
        if 'quota' in pool:
            print("\n📊 Quota:")
            print("-" * 60)
            quota = pool['quota']
            print(f"   Max Jobs: {quota.get('maxJobs', 'N/A')}")
            print(f"   Max GPU Per Job: {quota.get('maxGpuPerJob', 'N/A')}")
        
        if 'nodes' in pool and pool['nodes']:
            print("\n🖥️  Nodes:")
            print("-" * 60)
            for node in pool['nodes']:
                print(f"   - {node}")
        
        if 'jobs' in pool and pool['jobs']:
            print("\n📋 Running Jobs:")
            print("-" * 60)
            for job in pool['jobs']:
                print(f"   - {job['name']} (GPU: {job.get('gpu', 0)})")
        
        return 0
    except Exception as e:
        print(f"❌ Error describing pool: {e}")
        return 1
