/**
 * Public health-education articles. Editorial rules (enforced by scripts/compliance-lint.mjs):
 *  - general information about health and behaviour, never about a specific prescription product;
 *  - every factual claim has a reference; every article has a clinical reviewer and review date
 *    before it is published (status "draft" pages show a visible banner until then);
 *  - no testimonials, outcome promises or before/after imagery.
 */
export interface Article {
  slug: string;
  title: string;
  summary: string;
  readMinutes: number;
  status: "draft" | "published";
  reviewer: string | null;
  reviewedAt: string | null;
  sections: { heading: string; body: string[] }[];
  references: string[];
}

export const ARTICLES: Article[] = [
  {
    slug: "keep-muscle-while-changing-body-composition",
    title: "Keeping muscle while your body composition changes",
    summary: "Why strength training and protein matter whenever you're eating less — and what that means for your plan.",
    readMinutes: 5,
    status: "draft",
    reviewer: null,
    reviewedAt: null,
    sections: [
      {
        heading: "Weight is not the whole story",
        body: [
          "When people eat less than they burn, the weight they lose comes from both fat and lean tissue, including muscle. How much comes from each depends on several things, including how much protein you eat and whether you keep your muscles working.",
          "Muscle matters for more than appearance. It underpins strength, balance, blood-sugar handling and the ability to stay independent as you age.",
        ],
      },
      {
        heading: "What the research shows",
        body: [
          "A systematic review of studies in middle-aged and older adults found that combining energy restriction with exercise — particularly resistance exercise — reduced the loss of fat-free mass compared with energy restriction alone.",
          "Canada's 24-Hour Movement Guidelines recommend muscle-strengthening activities using major muscle groups at least twice a week for adults, alongside 150 minutes of moderate-to-vigorous aerobic activity.",
        ],
      },
      {
        heading: "What it means for your Blueprint",
        body: [
          "Every RECLAIM plan includes at least two strength sessions a week, adapted to pain and experience, and a daily protein target set with your coach.",
          "We track strength tests — like the 30-second sit-to-stand — alongside the scale and waist, so you can see whether you're keeping what matters.",
        ],
      },
    ],
    references: [
      "Weinheimer EM, Sands LP, Campbell WW. A systematic review of the separate and combined effects of energy restriction and exercise on fat-free mass in middle-aged and older adults: implications for sarcopenic obesity. Nutr Rev. 2010;68(7):375–388.",
      "Canadian Society for Exercise Physiology. Canadian 24-Hour Movement Guidelines for Adults aged 18–64 years and Adults aged 65 years or older. 2020. csepguidelines.ca",
    ],
  },
  {
    slug: "protein-how-much-and-when",
    title: "Protein: how much, and when",
    summary: "A practical guide to spreading protein through the day, with the evidence behind the targets.",
    readMinutes: 4,
    status: "draft",
    reviewer: null,
    reviewedAt: null,
    sections: [
      {
        heading: "Why protein needs rise with training",
        body: [
          "A meta-analysis of resistance-training studies found protein supplementation increased gains in muscle size and strength, with benefit levelling off at around 1.6 g of protein per kilogram of body weight per day.",
          "For older adults, an international expert group recommended 1.0–1.2 g/kg/day for healthy older people, and more for those who are active or recovering from illness.",
        ],
      },
      {
        heading: "Spread it out",
        body: [
          "Many people eat most of their protein at dinner. A simple first step is a palm-sized portion of protein at breakfast and lunch as well.",
          "If you have kidney disease or another medical condition, ask your clinician or a registered dietitian before changing your protein intake.",
        ],
      },
    ],
    references: [
      "Morton RW, Murphy KT, McKellar SR, et al. A systematic review, meta-analysis and meta-regression of the effect of protein supplementation on resistance training-induced gains in muscle mass and strength in healthy adults. Br J Sports Med. 2018;52(6):376–384.",
      "Bauer J, Biolo G, Cederholm T, et al. Evidence-based recommendations for optimal dietary protein intake in older people: a position paper from the PROT-AGE Study Group. J Am Med Dir Assoc. 2013;14(8):542–559.",
    ],
  },
  {
    slug: "sleep-and-appetite",
    title: "Sleep and appetite",
    summary: "What controlled studies show about short sleep, hunger and body composition — and three changes to try first.",
    readMinutes: 4,
    status: "draft",
    reviewer: null,
    reviewedAt: null,
    sections: [
      {
        heading: "Short sleep changes hunger",
        body: [
          "In a laboratory study of healthy young men, two nights of restricted sleep lowered leptin, raised ghrelin and increased self-reported hunger and appetite.",
          "In another controlled study of adults on a reduced-calorie diet, sleeping 5.5 hours rather than 8.5 hours reduced the share of weight lost as fat and increased the loss of fat-free mass.",
        ],
      },
      {
        heading: "Three changes to try first",
        body: [
          "Keep the same wake time every day, including weekends. Dim screens for the last hour before bed. Log your sleep for a week so your coach can see the pattern.",
          "Loud snoring, gasping at night or daytime sleepiness can be signs of a sleep disorder — talk to a clinician.",
        ],
      },
    ],
    references: [
      "Spiegel K, Tasali E, Penev P, Van Cauter E. Brief communication: sleep curtailment in healthy young men is associated with decreased leptin levels, elevated ghrelin levels, and increased hunger and appetite. Ann Intern Med. 2004;141(11):846–850.",
      "Nedeltcheva AV, Kilkus JM, Imperial J, Schoeller DA, Penev PD. Insufficient sleep undermines dietary efforts to reduce adiposity. Ann Intern Med. 2010;153(7):435–441.",
    ],
  },
];

export const articleBySlug = (slug: string) => ARTICLES.find((a) => a.slug === slug);
