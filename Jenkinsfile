library('pipeline-library@feature/add-with-ecr')

pipeline {
  options { timestamps() }
  agent any
  environment {
    SERVICE = 'kmstool'
    GITHUB_KEY = 'Jenkins'
    GITHUB_URL = 'https://github.com/josephbmanley/kmstool'
    DOCKER_REGISTRY = '356438515751.dkr.ecr.us-east-1.amazonaws.com'
  }
  stages {
    stage('Version') {
      steps {
        // runs the automatic semver tool which will version, & tag,
        runAutoSemver()
      }
    }
    stage('Build') {
      steps {


        echo "Building ${env.SERVICE} docker image"

        // Docker build flags are set via the getDockerBuildFlags() shared library.
        sh "docker build ${getDockerBuildFlags()} -t ${env.DOCKER_REGISTRY}/${env.SERVICE}:${getVersion('-d')} ."

        sh "tar -czvf ${env.SERVICE}-${getVersion('-d')}.tar.gz kmstool"
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
            sh "docker push ${env.DOCKER_REGISTRY}/${env.SERVICE}:${getVersion('-d')}"
        }
        
        //Copy tar.gz file to s3 bucket
        sh "aws s3 cp ${env.SERVICE}-${getVersion('-d')}.tar.gz s3://rbn-ops-pkg-us-east-1/${env.SERVICE}/${env.SERVICE}-${getVersion('-d')}.tar.gz"

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
