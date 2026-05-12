# Autonomous SRE Agent for EKS

## Project Overview
This project implements an Autonomous Site Reliability Engineering (SRE) Agent deployed on Amazon EKS. The system utilizes Llama 3.3 (via Groq API) to analyze real-time metrics from Prometheus and execute automated remediation via Jenkins pipelines.

## Repository Structure
- **/terraform**: Infrastructure as Code for VPC, Networking, and EKS Cluster.
- **/sre-agent**: Python Flask application containing the AI decision logic.
- **/stable-app**: Baseline application used for stability benchmarking.
- **/buggy-app**: Test application designed with intentional crash-loops for AI validation.
- **/k8s-manifests**: Kubernetes Deployment and Service definitions.

## Technical Architecture
1. **Metrics Collection**: Prometheus scrapes performance data from the cluster.
2. **Analysis**: The SRE Agent queries Prometheus for anomalies (CPU spikes, CrashLoops).
3. **Reasoning**: Metrics are sent to Llama 3.3 to determine the root cause and required action.
4. **Remediation**: The Agent triggers Jenkins pipelines to Scale or Rollback deployments.

## Features & Implementation
- **AI Decision Making**: Integrated Groq API for intelligent incident response.
- **Automated Remediation**: Closed-loop automation between Monitoring and CI/CD.
- **Infrastructure**: Modular Terraform with OIDC Provider and Private Subnets.
- **Observability**: Full Prometheus/Grafana stack for real-time visibility.

## Setup Instructions
1. **Infrastructure**: Navigate to `/terraform` and run `terraform init` and `terraform apply`.
2. **Secrets**: Create Kubernetes secret `sre-agent-secrets` containing `groq-api-key` and `jenkins-api-token`.
3. **Monitoring**: Deploy Prometheus via Helm in the `observability` namespace.
4. **Agent**: Apply the manifest in `/k8s-manifests/agent.yaml`.

## Automation Workflows
- **Scale-Pipeline**: Triggered when AI detects resource exhaustion.
- **Rollback-Pipeline**: Triggered when AI detects high restart rates in `buggy-app`.
