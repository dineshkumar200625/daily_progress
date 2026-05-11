from flask import Flask, render_template_string

app = Flask(__name__)

HTML = '''
<!DOCTYPE html>
<html>
<head>
<title>Retro Flappy Bird</title>
<style>
body {
    background: black;
    color: #00ffcc;
    text-align: center;
    font-family: monospace;
}

#game {
    width: 400px;
    height: 500px;
    border: 4px solid #00ffcc;
    margin: auto;
    position: relative;
    overflow: hidden;
    background: #111;
}

#bird {
    width: 40px;
    height: 40px;
    background: yellow;
    border-radius: 50%;
    position: absolute;
    left: 60px;
    top: 200px;
}

.pipe {
    width: 60px;
    background: #00ffcc;
    position: absolute;
    right: -60px;
}

button {
    margin-top: 15px;
    padding: 10px 20px;
    background: #00ffcc;
    border: none;
    font-size: 18px;
}
</style>
</head>
<body>
<h1>Retro Flappy Bird - Stable Version</h1>

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
        birdTop += 5
        bird.style.top = birdTop + 'px'
    }, 80)

    pipeLoop = setInterval(createPipe, 2500)
}

function jump(){
    birdTop -= 55
    bird.style.top = birdTop + 'px'
}

function createPipe(){

    let gap = 150
    let topHeight = Math.floor(Math.random() * 200) + 50

    let topPipe = document.createElement('div')
    topPipe.classList.add('pipe')
    topPipe.style.height = topHeight + 'px'
    topPipe.style.top = '0px'

    let bottomPipe = document.createElement('div')
    bottomPipe.classList.add('pipe')
    bottomPipe.style.height = (500 - topHeight - gap) + 'px'
    bottomPipe.style.bottom = '0px'

    game.appendChild(topPipe)
    game.appendChild(bottomPipe)

    let pipeLeft = 400

    let movePipe = setInterval(() => {

        pipeLeft -= 5

        topPipe.style.left = pipeLeft + 'px'
        bottomPipe.style.left = pipeLeft + 'px'

        if(pipeLeft < -60){
            clearInterval(movePipe)
            topPipe.remove()
            bottomPipe.remove()
        }

    }, 80)
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