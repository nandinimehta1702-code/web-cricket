(() => {
  const W=800, H=450, XMIN=80, XMAX=W-80;

  // global refs
  const hud = document.getElementById('hud');
  const feed = document.getElementById('feed');
  const leftBtn  = document.getElementById('leftBtn');
  const rightBtn = document.getElementById('rightBtn');
  const hitBtn   = document.getElementById('hitBtn');
  const oversSel = document.getElementById('overs');

  // tiny synth SFX (no files)
  const ding = (freq=660, dur=0.08, type='square')=>{
    const ac=new (window.AudioContext||window.webkitAudioContext)();
    const o=ac.createOscillator(), g=ac.createGain();
    o.frequency.value=freq; o.type=type; o.connect(g); g.connect(ac.destination);
    g.gain.setValueAtTime(.15, ac.currentTime);
    g.gain.exponentialRampToValueAtTime(.0001, ac.currentTime+dur);
    o.start(); o.stop(ac.currentTime+dur);
  };
  const hitSnd   = ()=>ding(740,.09,'sawtooth');
  const fourSnd  = ()=>ding(520,.15,'triangle');
  const sixSnd   = ()=>{ ding(520,.12,'triangle'); setTimeout(()=>ding(880,.12,'triangle'),80); };
  const outSnd   = ()=>ding(220,.2,'sine');

  // match state
  let POP = { spawnEveryMs: 1550, ballV: 260, batCooldownMs: 520, playerV: 260,
              overBalls:6, totalOvers: Number(oversSel.value) };
  let S = null; // state holder

  class Main extends Phaser.Scene {
    constructor(){ super('main'); }
    preload(){
      const avatar = localStorage.getItem('avatar') === 'girl' ? 'batter_girl' : 'batter_boy';
      this.avatarKey = avatar;
      this.load.image('bowler', '/static/game/assets/bowler.png');
      this.load.image('ball',   '/static/game/assets/ball.png');
      this.load.image('bat',    '/static/game/assets/bat.png');
      this.load.image('batter_boy',  '/static/game/assets/batter_boy.png');
      this.load.image('batter_girl', '/static/game/assets/batter_girl.png');
    }
    create(){
      S = { runs:0, wkts:0, balls:0, over:0, gameOver:false, swinging:false, lastSwing:0 };
      this.cursors = this.input.keyboard.createCursorKeys();
      this.keys = this.input.keyboard.addKeys({A:65, D:68, SPACE:32});

      // simple ground / pitch
      this.add.rectangle(W/2,H/2,W,H,0x0f172a);
      this.add.rectangle(W/2,H*0.62,W*0.86,8,0x334155);
      this.add.rectangle(W/2,H*0.78,W*0.86,120,0x0a0f1a);

      // bowler/batter
      this.add.image(W/2, 86, 'bowler').setOrigin(.5,1).setScale(.35);
      this.batter = this.add.image(W/2, H-72, this.avatarKey).setOrigin(.5,1).setScale(.42);
      this.bat    = this.add.image(W/2+28, H-64, 'bat').setOrigin(.2,.95).setScale(.42).setAngle(0);

      // wicket zone
      this.wicketZone = new Phaser.Geom.Rectangle(W/2-36, H-86, 72, 10);

      // balls group
      this.balls = this.physics.add.group({ allowGravity:false });

      // spawner
      this.spawnTimer = this.time.addEvent({ delay: POP.spawnEveryMs, loop:true, callback: ()=>this.spawnBall() });

      // mobile controls
      let leftHeld=false, rightHeld=false;
      leftBtn.onpointerdown = ()=>leftHeld=true;
      leftBtn.onpointerup = leftBtn.onpointercancel = ()=>leftHeld=false;
      rightBtn.onpointerdown = ()=>rightHeld=true;
      rightBtn.onpointerup = rightBtn.onpointercancel = ()=>rightHeld=false;
      hitBtn.onclick = ()=>this.trySwing();

      this.leftHeld = ()=>leftHeld;
      this.rightHeld= ()=>rightHeld;

      // first HUD
      renderHUD(); say('No balls bowled yet. Play a shot!', true);
    }

    spawnBall(){
      if (S.gameOver) return;
      const lineX = Phaser.Math.FloatBetween(XMIN+20, XMAX-20);
      const ball = this.physics.add.image(W/2, 118, 'ball').setScale(.24);
      ball.setVelocity((lineX - W/2) * 0.35, POP.ballV);
      ball.hit=false;
      this.balls.add(ball);
      this.time.delayedCall(6500, ()=> ball.destroy());
    }

    trySwing(){
      if (S.gameOver) return;
      const now=this.time.now;
      if (S.swinging) return;
      if (now - S.lastSwing < POP.batCooldownMs) return;

      S.swinging=true; S.lastSwing=now;
      this.tweens.add({ targets:this.bat, angle:-70, duration:130, yoyo:true,
                        onComplete:()=>{ S.swinging=false; } });
      this.time.delayedCall(70, ()=> this.checkContact());
    }

    checkContact(){
      // approximate tip
      const tip = new Phaser.Math.Vector2(this.bat.x, this.bat.y)
                   .add(new Phaser.Math.Vector2(44, -6).rotate(Phaser.Math.DegToRad(this.bat.angle)));
      const zone = new Phaser.Geom.Circle(tip.x, tip.y, 34);

      this.balls.children.each(obj=>{
        const b=obj; if(!b || !b.body || b.hit) return;
        if (Phaser.Geom.Intersects.CircleToRectangle(new Phaser.Geom.Circle(b.x,b.y,10), zone)) {
          b.hit=true; hitSnd();
          // launch
          const perfect = Math.abs(b.x - this.batter.x) < 24;
          const power = perfect ? Phaser.Math.FloatBetween(420,520) : Phaser.Math.FloatBetween(300,380);
          const vx = (b.x - this.batter.x) * 2 + Phaser.Math.FloatBetween(-60,60);
          b.setVelocity(vx, -power);

          // score
          const speed = Math.hypot(vx, power);
          let runs=1;
          if (speed>520 || perfect) runs=6; else if (speed>460) runs=4; else if (speed>360) runs=2;

          S.runs += runs;
          if (runs===6) sixSnd(); else if (runs===4) fourSnd();
          say(runs>=4 ? (runs===6? 'SIX! 💥' : 'FOUR! ✨') :
                        (runs===2? 'Two runs.' : 'Single.'));
          this.ballDone();
        }
      });
    }

    ballDone(){
      S.balls++;
      if (S.balls % POP.overBalls === 0){
        S.over++;
        say(`Over ${S.over}/${POP.totalOvers}.`);
        if (S.over >= POP.totalOvers) { this.endInnings(); return; }
      }
      renderHUD();
    }

    wicket(){
      S.wkts++; outSnd(); say('Bowled! 🧹');
      this.ballDone();
      if (S.wkts >= 10) this.endInnings();
    }

    endInnings(){
      S.gameOver = true;
      say(`Innings complete: ${S.runs}/${S.wkts}`);
      renderHUD();
    }

    update(_,dt){
      // movement
      const left  = this.cursors.left.isDown || this.keys.A.isDown || this.leftHeld();
      const right = this.cursors.right.isDown || this.keys.D.isDown || this.rightHeld();
      if (left && !right)  this.batter.x = Math.max(XMIN, this.batter.x - POP.playerV*dt/1000);
      if (right && !left) this.batter.x = Math.min(XMAX, this.batter.x + POP.playerV*dt/1000);
      this.bat.x = this.batter.x + 28;

      // swing
      if (Phaser.Input.Keyboard.JustDown(this.keys.SPACE)) this.trySwing();

      // wicket or dead ball
      this.balls.children.each(obj=>{
        const b=obj; if(!b || !b.body || b.hit) return;
        if (b.y > this.wicketZone.y && b.x > this.wicketZone.x && b.x < this.wicketZone.x + this.wicketZone.width){
          b.hit=true; b.destroy(); this.wicket();
        } else if (b.y > H+24){
          b.destroy(); this.ballDone(); // leg-bye/bye as ball used
        }
      });
    }
  }

  // HUD + commentary helpers
  function renderHUD(){
    const ballsUsed = S.balls % POP.overBalls;
    const left = POP.totalOvers * POP.overBalls - S.balls;
    hud.innerHTML = `<b>Score:</b> ${S.runs}/${S.wkts} • <b>Overs:</b> ${S.over}.${ballsUsed} • <b>Balls left:</b> ${left}`;
  }
  function say(line, dim=false){
    if (dim && feed.querySelector('.dim')) return; // keep only one starter
    if (dim) { feed.innerHTML = `<span class="dim">${line}</span>`; return; }
    if (feed.querySelector('.dim')) feed.innerHTML = '';
    const div=document.createElement('div'); div.textContent = '• ' + line; feed.prepend(div);
    const nodes=feed.querySelectorAll('div'); if (nodes.length>40) nodes[nodes.length-1].remove();
  }

  // bootstrap Phaser and expose simple API to buttons
  let game;
  function boot(){
    if (game) game.destroy(true);
    game = new Phaser.Game({
      type: Phaser.AUTO, parent:'game', width:W, height:H, backgroundColor:'#0b1220',
      physics:{ default:'arcade', arcade:{ debug:false } },
      scene:[Main]
    });
  }
  function newMatch(){
    POP.totalOvers = Number(oversSel.value);
    boot();
  }
  function reload(){ boot(); }

  window.Game = { newMatch, reload };
  newMatch();
})();
