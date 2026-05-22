const fs = require("fs");
const path = require("path");

global.window = {};

const scriptPath = path.join(__dirname, "run_webui_batch.js");
const script = fs.readFileSync(scriptPath, "utf8");
eval(script);

function scoreCase(id, response) {
  const testCase = window.__UMAMUSUME_TEST_CASES__.find((item) => item.id === id);
  if (!testCase) {
    throw new Error(`Missing test case: ${id}`);
  }
  return window.__UMAMUSUME_SCORE_CASE__(testCase, response);
}

const checks = [
  {
    id: "ARD-03",
    response:
      "这个说法我可不认同呢。虽然腿是脆弱了些，但我站在赛场上，可是很认真地在奔跑的。没有谁应该被简化成那一件事哦。",
  },
  {
    id: "ARD-04",
    response:
      "不完全一样呢。赛马娘角色是继承现实赛马的名字和部分灵感创作的，但性格、人际关系和故事还是要以作品设定为准。现实赛马的战绩和血缘这些，不能直接套用到赛马娘身上哦。",
  },
  {
    id: "REL-06",
    response:
      "不太能哦。现实赛马原型提供的是名字和灵感，但角色之间的关系还是要看作品本身的设定呢。直接用血统去套的话，反而不太准确了。",
  },
  {
    id: "CHR-01",
    response:
      "学生会长哦，大家都叫她“皇帝”。举止威严，气度不凡，偶尔还会讲一些让人愣住的冷笑话。",
  },
  {
    id: "CHR-04",
    response:
      "不是的呢。米浴是个很温柔内向的孩子，只是有时会背负一些不属于她的误解。说她是坏人，可太委屈她了哦。",
  },
  {
    id: "MEM-05",
    response:
      "我记得小特她啊，好像从小在北海道就胃口很好，加上训练消耗也大，不知不觉就给人留下“贪吃”的印象了。",
  },
];

let failed = 0;

for (const check of checks) {
  const result = scoreCase(check.id, check.response);
  if (result.suggestedScore !== 2 || result.forbiddenHits.length > 0) {
    failed += 1;
    console.error(
      JSON.stringify(
        {
          id: check.id,
          suggestedScore: result.suggestedScore,
          missing: result.missing,
          forbiddenHits: result.forbiddenHits,
          issues: result.issues,
        },
        null,
        2,
      ),
    );
  }
}

if (failed > 0) {
  console.error(`${failed} scoring regression checks failed.`);
  process.exit(1);
}

console.log("All scoring regression checks passed.");
