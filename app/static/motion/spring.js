// motion/spring.js - Second-order Spring solver and CSS linear() generator

export class Spring {
  constructor({
    stiffness = 170,
    damping = 22,
    mass = 1,
    value = 0,
    velocity = 0,
    target = 0,
    precision = 0.0005,
  } = {}) {
    this.stiffness = stiffness;
    this.damping = damping;
    this.mass = mass;
    this.value = value;
    this.velocity = velocity;
    this.target = target;
    this.precision = precision;
  }

  // retarget keeps current value AND velocity for seamless reversal
  retarget(target) {
    this.target = target;
  }

  // Set physical parameters
  configure({ stiffness, damping, mass }) {
    if (stiffness !== undefined) this.stiffness = stiffness;
    if (damping !== undefined) this.damping = damping;
    if (mass !== undefined) this.mass = mass;
  }

  // Step simulation forward by dt seconds. Returns true when settled.
  step(dt) {
    dt = Math.min(dt, 1 / 30); // clamp after tab stalls
    const n = Math.max(1, Math.ceil(dt / (1 / 240))); // sub-step at 240Hz for stability
    const h = dt / n;

    for (let i = 0; i < n; i++) {
      const a = (-this.stiffness * (this.value - this.target) - this.damping * this.velocity) / this.mass;
      this.velocity += a * h; // semi-implicit Euler
      this.value += this.velocity * h;
    }

    if (Math.abs(this.velocity) < this.precision && Math.abs(this.value - this.target) < this.precision) {
      this.value = this.target;
      this.velocity = 0;
      return true; // settled
    }

    return false;
  }
}

// Simulates an open transition offline to find peak absolute velocity vmax
export function simulateVMax({ stiffness = 170, damping = 22, mass = 1, from = 0, to = 1 }) {
  const s = new Spring({ stiffness, damping, mass, value: from, velocity: 0, target: to, precision: 0.0001 });
  let peak = 0;
  const dt = 1 / 240;
  for (let step = 0; step < 2400; step++) {
    const settled = s.step(dt);
    const speed = Math.abs(s.velocity);
    if (speed > peak) peak = speed;
    if (settled) break;
  }
  return peak || 1.0;
}

// Generates CSS linear() easing function by sampling the step response
export function generateLinearEasing({ stiffness = 170, damping = 22, mass = 1 }, steps = 54, duration = 0.55) {
  const w0 = Math.sqrt(stiffness / mass);
  const z = damping / (2 * Math.sqrt(stiffness * mass));
  
  const sample = (t) => {
    if (z < 1) {
      const wd = w0 * Math.sqrt(1 - z * z);
      return 1 - Math.exp(-z * w0 * t) * (Math.cos(wd * t) + (z * w0 / wd) * Math.sin(wd * t));
    }
    return 1 - Math.exp(-w0 * t) * (1 + w0 * t);
  };

  const pts = [];
  for (let i = 0; i <= steps; i++) {
    const t = (i / steps) * duration;
    const v = sample(t);
    pts.push(Number(v.toFixed(4)));
  }
  return `linear(${pts.join(", ")})`;
}
