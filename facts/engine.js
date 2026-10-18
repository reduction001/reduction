(function(root){
'use strict';
class FactEngine{
 constructor(facts,random=Math.random){this.facts=facts;this.random=random;this.filter='all';this.bags=new Map();this.trail=[];this.position=-1;}
 get current(){return this.position>=0?this.trail[this.position].fact:null;}
 get pool(){return this.facts.filter(f=>this.filter==='all'||f.industry_slug===this.filter);}
 get canBack(){return this.position>0;}
 shuffle(items){const a=[...items];for(let i=a.length-1;i>0;i--){const j=Math.floor(this.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
 append(fact){this.trail=this.trail.slice(0,this.position+1);this.trail.push({fact,filter:this.filter});if(this.trail.length>2000)this.trail.shift();this.position=this.trail.length-1;return fact;}
 next(){const pool=this.pool;if(!pool.length)return null;let bag=this.bags.get(this.filter)||[];if(!bag.length)bag=this.shuffle(pool);if(this.current&&bag[bag.length-1].id===this.current.id){if(bag.length>1)[bag[0],bag[bag.length-1]]=[bag[bag.length-1],bag[0]];else if(pool.length>1)bag=this.shuffle(pool.filter(f=>f.id!==this.current.id));}const fact=bag.pop();this.bags.set(this.filter,bag);return this.append(fact);}
 setFilter(value){this.filter=value==='all'||this.facts.some(f=>f.industry_slug===value)?value:'all';return this.next();}
 open(id,filter='all'){const f=this.facts.find(f=>f.id===id);if(!f)return this.setFilter(filter);this.filter=filter==='all'||f.industry_slug===filter?filter:f.industry_slug;const pool=this.pool.filter(x=>x.id!==f.id);this.bags.set(this.filter,this.shuffle(pool));return this.append(f);}
 back(){if(!this.canBack)return null;this.position--;const entry=this.trail[this.position];this.filter=entry.filter;return entry.fact;}
}
root.ReductionFactEngine=FactEngine;
if(typeof module!=='undefined'&&module.exports)module.exports=FactEngine;
})(typeof globalThis!=='undefined'?globalThis:this);
