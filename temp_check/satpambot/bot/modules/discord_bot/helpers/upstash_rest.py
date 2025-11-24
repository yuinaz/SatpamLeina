# -*- coding: utf-8 -*-
import os, httpx, json

URL = os.getenv("UPSTASH_REDIS_REST_URL")
TOK = os.getenv("UPSTASH_REDIS_REST_TOKEN")
HDR = {"Authorization": f"Bearer {TOK}", "Content-Type":"application/json"}

def cmd(*arr):
    if not URL or not TOK:
        raise RuntimeError("Upstash env missing")
    with httpx.Client(timeout=10.0) as x:
        r = x.post(URL, headers=HDR, json=list(arr))
        r.raise_for_status()
        return r.json()

def get(key:str):
    return cmd("GET", key)

def set(key:str, val:str):
    return cmd("SET", key, str(val))

def incrby(key:str, delta:int):
    return cmd("INCRBY", key, str(int(delta)))

def json_arrappend(key:str, path:str, value:dict):
    return cmd("JSON.ARRAPPEND", key, path, json.dumps(value))

def sadd(key:str, member:str):
    return cmd("SADD", key, member)

def expire(key:str, ttl:int):
    return cmd("EXPIRE", key, str(int(ttl)))
