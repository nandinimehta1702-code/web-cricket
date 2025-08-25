(() => {
  // ---------- config ----------
  const W = 1000, H = 560;
  const RANGE_XL = 140, RANGE_XR = W - 140;

  const POP = {
    ballSpeedY: 270,         // delivery speed
    spawnEveryMs: 1600,      // ball every ~1.6s
    playerSpeed: 320,        // lateral move
    batCooldownMs: 500,
    batWindowDelayMs: 90,
    overBalls: 6,
  };

  // scale tuning for your images
  const SCALE = {
    bowler: 0.35,
    batter: 0.35,
    bat:    0.38,
    ball:   0.14,
  };

  // ---------- game state ----------
  const state = {
    runs: 0, wkts: 0, balls: 0, overs: 2,
    swinging: false, lastSwing: 0,
    gameOver: false,
  };

  const savedAvatar = localStorage.getItem('avatar') || 'boy';

  // ---------- preload/create ----------
  class Main extends Phaser.Scene {
    constructor(){ super('main'); }

    preload(){
      // images must exist at these paths
      this.load.image('bowler', '/static/game/assets/bowler.png');
      this.load.image('batter_boy', '/static/game/assets/batter_boy.png');
      this.load.image('batter_girl','/static/game/assets/batter_girl.png');
      this.load.image('bat',    '/static/game/assets/bat.png');
      this.load.image('ball',   '/static/game/assets/ball.png');
    }

    create(){
      // background + pitch
      this.add.rectangle(W/2, H/2, W, H, 0x0b1220).setDepth(0);
      this.add.rectangle(W/2, H*0.62, W*0.86, 8, 0x334155).setDepth(1);
      this.add.rectangle(W/2, H*0.78, W*0.86, 140, 0x0a0f1a).setDepth(1);

      // bowler
      this.bowler = this.add.image(W/2, 110, 'bowler').setScale(SCALE.bowler).setDepth(2);

      // batter + bat
      const key = (localStorage.getItem('avatar') || 'boy') === 'girl' ? 'batter_girl' : 'batter_boy';
      this.batter = this.add.image(W/2, H-110, key).setScale(SCALE.batter).setDepth(4);
      this.bat = this.add.image(this.batter.x + 36, this.batter.y - 16, 'bat')
                     .setScale(SCALE.bat).setOrigin(0.25, 1.0).setDepth(5).setAngle(0);

      // wicket zone (invisible collider area)
      this.wicketZone = new Phaser.Geom.Rectangle(W/2 - 30, H-96, 60, 16);

      // physics group for balls
      this.balls = this.physics.add.group({ allowGravity:false });

      // controls
      this.cursors = this.input.keyboard.createCursorKeys();
      this.keys = this.input.keyboard.addKeys({
        A:Phaser.Input.Keyboard.KeyCodes.A,
        D:Phaser.Input.Keyboard.KeyCodes.D,
        SPACE:Phaser.Input.Keyboard.KeyCodes.SPACE
      });

      // mobile buttons
      const leftBtn  = document.getElementById('leftBtn');
      const rightBtn = document.getElementById('rightBtn');
      const hitBtn   = document.getElementById('hitBtn');
      let leftHeld=false, rightHeld=false;
      leftBtn.onpointerdown = ()=> leftHeld = true;
      leftBtn.onpointerup   = leftBtn.onpointercancel = ()=> leftHeld=false;
      rightBtn.onpointerdown = ()=> rightHeld = true;
      rightBtn.onpointerup   = rightBtn.onpointercancel = ()=> rightHeld=false;
      hitBtn.onclick = ()=> this.trySwing();
      this.leftHeldRef = ()=> leftHeld;
      this.rightHeldRef = ()=> rightHeld;

      // UI: overs/new/pick
      document.getElementById('overs').onchange = (e)=>{
        const val = e.target.value.split(' ')[0]; // "2 over(s)"
        state.overs = parseInt(val, 10) || 2;
        this.resetInnings();
      };
      document.getElementById('newBtn').onclick = ()=> this.resetInnings();
      document.getElementById('pickBtn').onclick = ()=>{
        const next = (localStorage.getItem('avatar') || 'boy') === 'boy' ? 'girl' : 'boy';
        localStorage.setItem('avatar', next);
        this.swapAvatar(next);
      };

      // start bowling
      this.spawnTimer = this.time.addEvent({
        delay: POP.spawnEveryMs, loop: true, callback: ()=> this.spawnBall()
      });

      this.updateHUD();
    }

    swapAvatar(who){
      const key = who === 'girl' ? 'batter_girl' : 'batter_boy';
      this.batter.setTexture(key);
      // keep scale & position
    }

    resetInnings(){
      state.runs = 0; state.wkts = 0; state.balls = 0; state.gameOver = false;
      // clear any live balls
      this.balls.getChildren().forEach(b => b.destroy());
      this.updateHUD();
    }

    spawnBall(){
      if(state.gameOver) return;
      const lineX = Phaser.Math.Between(RANGE_XL, RANGE_XR);
      const img = this.add.image(W/2, 150, 'ball').setScale(SCALE.ball).setDepth(3);
      const body = this.physics.add.existing(img);
      body.body.allowGravity = false;
      body.body.setVelocity((lineX - W/2) * 0.45, POP.ballSpeedY);
      img.hit = false;

      // destroy after a while to avoid leaks
      this.time.delayedCall(7000, ()=> img.destroy());
      this.balls.add(img);
    }

    trySwing(){
      if(state.gameOver) return;
      const now = this.time.now;
      if(state.swinging || now - state.lastSwing < POP.batCooldownMs) return;

      state.swinging = true;
      state.lastSwing = now;

      // swing anim
      this.tweens.add({
        targets: this.bat, angle: -70, duration: 140, yoyo: true,
        onComplete: ()=> { state.swinging = false; }
      });

      // check contact slightly after starting swing
      this.time.delayedCall(POP.batWindowDelayMs, ()=> this.checkContact());
    }

    checkContact(){
      // circle near bat tip
      const rad = Phaser.Math.DegToRad(this.bat.angle - 90);
      const tipX = this.bat.x + Math.cos(rad) * 48;
      const tipY = this.bat.y + Math.sin(rad) * 48;
      const zone = new Phaser.Geom.Circle(tipX, tipY, 30);

      this.balls.getChildren().forEach(b => {
        if(!b || b.hit || !b.body) return;
        const c = new Phaser.Geom.Circle(b.x, b.y, 20);
        if(Phaser.Geom.Intersects.CircleToCircle(zone, c)){
          b.hit = true;
          const perfect = Math.abs(b.x - this.batter.x) < 22;
          const vx = (b.x - this.batter.x) * 3 + Phaser.Math.Between(-80, 80);
          const vy = perfect ? -520 : Phaser.Math.Between(-420, -320);
          b.body.setVelocity(vx, vy);
          // score
          let runs = perfect ? 6 : (Math.abs(vx)+Math.abs(vy) > 720 ? 4 : (Math.abs(vx) > 260 ? 2 : 1));
          state.runs += runs;
          this.ballDone();
        }
      });
    }

    ballDone(){
      state.balls++;
      if(state.balls >= state.overs * POP.overBalls){
        state.gameOver = true;
      }
      this.updateHUD();
    }

    wicket(){
      state.wkts++;
      this.ballDone();
      if(state.wkts >= 10) state.gameOver = true;
      this.updateHUD();
    }

    updateHUD(){
      const o = Math.floor(state.balls / POP.overBalls);
      const b = state.balls % POP.overBalls;
      const left = state.overs * POP.overBalls - state.balls;
      document.getElementById('hud').innerHTML =
        `<b>Score:</b> ${state.runs}/${state.wkts} &nbsp;•&nbsp; <b>Overs:</b> ${o}.${b} &nbsp;•&nbsp; <b>Balls left:</b> ${left}`;
    }

    update(_, dt){
      // move batter
      const left = this.cursors.left.isDown || this.keys.A.isDown || this.leftHeldRef();
      const right= this.cursors.right.isDown|| this.keys.D.isDown || this.rightHeldRef();
      if(left && !right)  this.batter.x = Math.max(RANGE_XL, this.batter.x - POP.playerSpeed * dt/1000);
      if(right && !left) this.batter.x = Math.min(RANGE_XR, this.batter.x + POP.playerSpeed * dt/1000);
      // keep bat next to batter
      this.bat.x = this.batter.x + 36;

      if(Phaser.Input.Keyboard.JustDown(this.keys.SPACE)) this.trySwing();

      // wicket check / ball finished
      this.balls.getChildren().forEach(b => {
        if(!b || !b.body || b.hit) return;
        if(b.y > this.wicketZone.y && b.x > this.wicketZone.x && b.x < this.wicketZone.x + this.wicketZone.width){
          b.hit = true; b.destroy(); this.wicket();
        } else if (b.y > H + 40) {
          b.destroy(); this.ballDone();
        }
      });
    }
  }

  const cfg = {
    type: Phaser.AUTO, parent:'game', width: W, height: H, backgroundColor: '#0b1220',
    physics: { default:'arcade', arcade:{ debug:false } },
    scene: [Main]
  };
  new Phaser.Game(cfg);
})();
