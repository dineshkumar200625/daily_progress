pipeline {

    agent any

    stages {

        stage('Deploy Stable App') {

            steps {

                sh '''

                ssh -o StrictHostKeyChecking=no \
                ubuntu@13.48.104.167 "

                cd /home/ubuntu/stable-python-app

                git pull

                kubectl apply -f stable-app.yaml

                "

                '''
            }
        }
    }
}
