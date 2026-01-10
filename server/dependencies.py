from fastapi import Depends
from gpuctl.client.pool_client import PoolClient
from gpuctl.client.job_client import JobClient


def get_pool_client():
    """获取资源池客户端依赖"""
    return PoolClient()


def get_job_client():
    """获取作业客户端依赖"""
    return JobClient()
