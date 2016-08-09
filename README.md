# dynamodb-lock

dynamodb-lock is based on https://github.com/joeabrams026/dynamo-lock, a node.js and dynamodb based locking client. It supports autoexpiring locks, spinning for a lock and manually releasing a lock. It's designed primarily for use in AWS Lambda code, but can be used elsewhere without modification.

It needs better docs, exception handling and testing, but the guts are currently there. Patches welcome!

# Usage
```python
lock = Lockerclient('mylocktable')
```
If necessary, create the lock table.

```python
lock.create_lock_table()
```

Attempt to aquire a lock. Returns True or False if succeeded.

```python
timeout = 1000  # 1000 milliseconds is one second
lock.get_lock('mylock', timeout)
```

Alternatively, spin for a lock if locks are bound to be short lived and you can spare the cpu.

```python
lock.spinlock('mylock', 10)
```

Finally, release your lock

```python
lock.release_lock('mylock', 10)
```
