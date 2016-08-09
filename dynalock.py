#!/usr/bin/env python2.7

import boto3
import uuid
import time


def millis_in_future(millis):
    return time.time() + (millis/1000.0)


class LockerClient():

    def __init__(self, lockTableName):
        self.lockTableName = lockTableName
        self.db = boto3.client('dynamodb')
        self.locked = False
        self.guid = ""

    def get_lock(self, lockName, timeoutMillis):
        # First get the row for 'name'
        get_item_params = {
            'TableName': self.lockTableName,
            'Key': {
                'name': {
                    'S': lockName,
                }
            },
            'AttributesToGet': [
                'guid', 'expiresOn'
            ],
            'ConsistentRead': True,
        }

        # Generate a GUID for our lock
        guid = str(uuid.uuid4())

        put_item_params = {
            'Item': {
                'name': {
                    'S': lockName
                },
                'guid': {
                    'S': guid
                },
                'expiresOn': {
                    'N': str(millis_in_future(timeoutMillis))
                }
            },
            'TableName': self.lockTableName
        }

        try:
            data = self.db.get_item(**get_item_params)
            now = time.time()

            if 'Item' not in data:
                # Table exists, but lock not found. We'll try to add a lock
                # If by the time we try to add we find that the attribute guid exists (because another client grabbed it), the lock will not be added
                put_item_params['ConditionExpression'] = 'attribute_not_exists(guid)'

            # We know there's possibly a lock'. Check to see it's expired yet
            elif float(data['Item']['expiresOn']['N']) > now:
                return False
            else:
                # We know there's possibly a lock and it's expired. We'll take over, providing that the guid of the lock we read as expired is the one we're
                # taking over from. This is an atomic conditional update
                print("Expired lock found. Attempting to aquire")
                put_item_params['ExpressionAttributeValues'] = {
                    ':oldguid': {'S': data['Item']['guid']['S']}
                }
                put_item_params['ConditionExpression'] = "guid = :oldguid"
        except Exception as e:
            print("Exception" + str(e))
            # Something nasty happened. Possibly table not found
            return False

        # now we're going to try to get the lock. If ANY exception happens, we assume no lock
        try:
            self.db.put_item(**put_item_params)
            self.locked = True
            self.guid = guid
            return True
        except Exception:
            return False

    def release_lock(self, lockName):
        if not self.locked:
            return

        delete_item_params = {
            'Key': {
                'name': {
                    'S': lockName,
                }
            },
            'ExpressionAttributeValues': {
                    ':ourguid': {'S': self.guid}
            },
            'TableName': self.lockTableName,
            'ConditionExpression': "guid = :ourguid"
        }

        try:
            self.db.delete_item(**delete_item_params)
            self.locked = False
            self.guid = ""
        except Exception as e:
            print(str(e))

    def spinlock(self, lockName, timeoutMillis):
        while not self.get_lock(lockName, timeoutMillis):
            pass

    def create_lock_table(self):
        response = self.db.create_table(
            AttributeDefinitions=[
                {
                    'AttributeName': 'name',
                    'AttributeType': 'S'
                },
            ],
            TableName=self.lockTableName,
            KeySchema=[
                {
                    'AttributeName': 'name',
                    'KeyType': 'HASH'
                },
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 1,
                'WriteCapacityUnits': 1
            }
        )
        print(response)

    def delete_lock_table(self):
        self.db.delete_table(TableName=self.lockTableName)
