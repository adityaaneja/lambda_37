import os.path
import yaml
import boto3
from kubernetes import client, config
import auth

# Configure your cluster name and region here
KUBE_FILEPATH = '/tmp/kubeconfig'
CLUSTER_NAME = 'aditya-test-cluster'
REGION = 'us-east-1'

# We assume that when the Lambda container is reused, a kubeconfig file exists.
# If it does not exist, it creates the file.

if not os.path.exists(KUBE_FILEPATH):
    kube_content = dict()
    # Get data from EKS API
    eks_api = boto3.client('eks',region_name=REGION)
    cluster_info = eks_api.describe_cluster(name=CLUSTER_NAME)
    certificate = cluster_info['cluster']['certificateAuthority']['data']
    endpoint = cluster_info['cluster']['endpoint']

    # Generating kubeconfig
    kube_content = dict()

    kube_content['apiVersion'] = 'v1'
    kube_content['clusters'] = [
        {
        'cluster':
            {
            'server': str(endpoint),
            'certificate-authority-data': str(certificate)
            },
        'name':'kubernetes'
        }]

    kube_content['contexts'] = [
        {
        'context':
            {
            'cluster':'kubernetes',
            'user':'aws'
            },
        'name':'aws'
        }]

    kube_content['current-context'] = 'aws'
    kube_content['Kind'] = 'Config'
    kube_content['users'] = [
    {
    'name':'aws',
    'user': {
        'name': 'lambda'
    }
    }]

    # Write kubeconfig
    with open(KUBE_FILEPATH, 'w') as outfile:
        yaml.dump(kube_content, outfile, default_flow_style=False)
    
    #Enable this to check the kubeconfig in Lambda logs 
    with open(KUBE_FILEPATH,'r') as file_object:
        print(yaml.safe_load(file_object))
    

def handler(event, context):

    # Get Token
    eks = auth.EKSAuth(CLUSTER_NAME)
    token = eks.get_token()
    #This token will be used to make api calls to Kubenetes API server
    print(token)
    # Configure
    config.load_kube_config(KUBE_FILEPATH)

    
    configuration = client.Configuration.get_default_copy() # Need to call get.default_copy() method for python kubenetes module > 11.0
    configuration.api_key['authorization'] = token
    configuration.api_key_prefix['authorization'] = 'Bearer'

    
    # Set up API object
    api = client.ApiClient(configuration)
    v1 = client.CoreV1Api(api)
    
    # Get all the pods by calling v1 (API Object) method
    ret = v1.list_namespaced_pod("default")

    for i in ret.items:
        print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
