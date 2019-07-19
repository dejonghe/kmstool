library('pipeline-library')

pipeline {
  options { timestamps() }
  agent any
  environment {
    SERVICE = 'kmstool'
    GITHUB_KEY = 'kmstoolDeployKey'
    GITHUB_URL = 'git@github.com:dejonghe/kmstool.git'
    DOCKER_REGISTRY = '356438515751.dkr.ecr.us-east-1.amazonaws.com'
  }
  stages {
    stage("Pull Versioning Image")
    {
        steps
        {
          withEcr {
            sh "docker pull ${DOCKER_REGISTRY}/auto-semver"
          }
        }
    }
    stage('Version') {
        agent {
            docker {
                image "${DOCKER_REGISTRY}/auto-semver"
            }
        }
      steps {
        // runs the automatic semver tool which will version, & tag,
        runAutoSemver()

        //Grabs current version
        script
        {
            env.VERSION = getVersion('-d')
        }
      }
      post{
        // Update Git with status of version stage.
        success {
          updateGithubCommitStatus(GITHUB_URL, 'Passed version stage', 'SUCCESS', 'Version')
        }
        failure {
          updateGithubCommitStatus(GITHUB_URL, 'Failed version stage', 'FAILURE', 'Version')
        }
      }
    }
    stage('Build') {
      steps {


        echo "Building ${env.SERVICE} docker image"

        // Docker build flags are set via the getDockerBuildFlags() shared library.
        sh "docker build ${getDockerBuildFlags()} -t ${env.DOCKER_REGISTRY}/${env.SERVICE}:${env.VERSION} ."

        sh "tar -czvf ${env.SERVICE}-${env.VERSION}.tar.gz kmstool"
      }
      post{
        // Update Git with status of build stage.
        success {
          updateGithubCommitStatus(GITHUB_URL, 'Passed build stage', 'SUCCESS', 'Build')
        }
        failure {
          updateGithubCommitStatus(GITHUB_URL, 'Failed build stage', 'FAILURE', 'Build')
        }
      }
    }
    stage('Push')
    {
      steps {     
        withEcr {
            sh "docker push ${env.DOCKER_REGISTRY}/${env.SERVICE}:${env.VERSION}"
        }
        
        //Copy tar.gz file to s3 bucket
        sh "aws s3 cp ${env.SERVICE}-${env.VERSION}.tar.gz s3://rbn-ops-pkg-us-east-1/${env.SERVICE}/${env.SERVICE}-${env.VERSION}.tar.gz"

      }
      post{
        // Update Git with status of push stage.
        success {
          updateGithubCommitStatus(GITHUB_URL, 'Passed push stage', 'SUCCESS', 'Push')
        }
        failure {
          updateGithubCommitStatus(GITHUB_URL, 'Failed push stage', 'FAILURE', 'Push')
        }
      }
    }
  }
  post {
    always {
      removeDockerImages()
      cleanWs()
    }
  }
}
