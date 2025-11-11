#!/bin/bash

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"  # Cambia si usas otra región
REPO_NAME="lambda_final_repo"
IMAGE_TAG="latest"


aws ecr describe-repositories --repository-names $REPO_NAME --region $REGION >/dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "Creando repositorio $REPO_NAME en ECR..."
  aws ecr create-repository --repository-name $REPO_NAME --region $REGION
fi


echo "Iniciando sesión en ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com


echo "Construyendo la imagen Docker..."
docker build -t $REPO_NAME .


echo "Etiquetando imagen..."
docker tag $REPO_NAME:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:$IMAGE_TAG


echo "Subiendo imagen a ECR..."
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:$IMAGE_TAG

echo "Imagen publicada en ECR con éxito."
