import boto3
import os
ec2 = boto3.resource('ec2')
client = boto3.client('transcribe')

def list_instance_name():
    response = ec2.describe_instances()
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            # This sample print will output entire Dictionary object
            # print(instance)
            # This will print will output the value of the Dictionary key 'InstanceId'
            # print(instance["InstanceId"])
            for tag in instance["Tags"]:
                if tag['Key'] == 'Name':
                    print(tag['Value'])

def create_private_key():

    if os.path.exists('./keys'):
        os.mkdir('./keys')
    # create a file to store the key locally
    outfile = open('./keys/trading_bot.pem', 'w')

    # call the boto ec2 function to create a key pair
    ec2.delete_key_pair(KeyName='trading_bot')
    key_pair = ec2.create_key_pair(KeyName='trading_bot')

    print(key_pair['KeyMaterial'])

    # capture the key and store it in a file
    outfile.write(str(key_pair['KeyMaterial']))

def create_bot():
    user_data = """
    #!/bin/bash
    echo "This command ran on $(date)" > test.text
    """

    # create a new EC2 instance
    instances = ec2.create_instances(
        ImageId='ami-0817d428a6fb68645',
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        KeyName='trading_bot',
        UserData=user_data
    )
    print(instances)


def run_command():
    ssm = boto3.client('ssm')

    response = ssm.send_command(
        InstanceIds=['i-0c6963e6e016ceb32'],
        DocumentName='AWS-RunShellScript',
        Parameters={'commands': ['echo "This command ran on $(date)"']}
    )
    command_id = response['Command']['CommandId']
    print(command_id)
    feedback = ssm.get_command_invocation(CommandId=command_id, InstanceId='i-0a93c574bb48e4233')

    print(feedback['StandardOutputContent'])


create_private_key()
# create_bot()