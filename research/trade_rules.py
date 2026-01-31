rules = [
  {
    "name": "rules_v2_time_adx",
    "skip": [
      {
        "time_bucket": "0-30",
        "adx_bucket": "(25.0, 40.0]"
      }
    ],
    "size": [
      {
        "time_bucket": "90-180",
        "adx_bucket": "(25.0, 40.0]",
        "mult": 0.5
      },
      {
        "time_bucket": "180-300",
        "mult": 1
      }
    ]
  },
  {
    "name": "rules_v2_time_adx_vwap",
    "skip": [
      {
        "time_bucket": "0-30",
        "adx_bucket": "(25.0, 40.0]"
      },
      {
        "time_bucket": "30-90",
        "vwap_atr_bucket": "(-1.0, -0.25]"
      }
    ],
    "size": [
      {
        "time_bucket": "90-180",
        "adx_bucket": "(25.0, 40.0]",
        "mult": 0.5
      },
      {
        "time_bucket": "0-30",
        "vwap_atr_bucket": "(-0.25, 0.25]",
        "adx_bucket": "(-0.001, 15.0]",
        "mult": 0.5
      },
      {
        "time_bucket": "180-300",
        "mult": 1
      }
    ]
  },
  {
    "name": "rules_v3_time_bb",
    "skip": [
      {
        "time_bucket": "30-90",
        "bb_bucket": "(0.0, 0.25]"
      }
    ],
    "size": [
      {
        "time_bucket": "0-30",
        "bb_bucket": "(0.25, 0.75]",
        "mult": 0.5
      }
    ]
  },
  {
    "name": "rules_v4_time_vix1d",
    "skip": [
      {
        "time_bucket": "0-30",
        "vix1d_bucket": "(14.32, inf]"
      }
    ],
    "size": [
      {
        "time_bucket": "30-90",
        "vix1d_bucket": "(14.32, inf]",
        "mult": 0.5
      },
      {
        "time_bucket": "180-300",
        "vix1d_bucket": "(14.32, inf]",
        "mult": 1.25
      }
    ]
  },
  {
    "name": "rules_v5_time_cushion",
    "skip": [
      {
        "time_bucket": "0-30",
        "cushion_norm_bucket": "(-inf, 0.25]"
      }
    ],
    "size": [
      {
        "time_bucket": "30-90",
        "cushion_norm_bucket": "(-inf, 0.25]",
        "mult": 0.5
      }
    ]
  },
  {
    "name": "rules_v6_time_maxloss",
    "skip": [
      {
        "time_bucket": "30-90",
        "max_loss_norm_bucket": "(6.0, 8.0]"
      }
    ],
    "size": [
      {
        "time_bucket": "0-30",
        "max_loss_norm_bucket": "(8.0, inf]",
        "mult": 0.75
      },
      {
        "time_bucket": "180-300",
        "max_loss_norm_bucket": "(8.0, inf]",
        "mult": 1.1
      }
    ]
  },
  {
    "name": "rules_v7_time_em",
    "skip": [
      {
        "time_bucket": "0-30",
        "em_bucket": "(2.897, inf]"
      },
      {
        "time_bucket": "30-90",
        "em_bucket": "(1.456, 2.034]"
      }
    ],
    "size": [
      {
        "time_bucket": "30-90",
        "em_bucket": "(0.929, 1.456]",
        "mult": 1.1
      },
      {
        "time_bucket": "180-300",
        "em_bucket": "(1.456, 2.034]",
        "mult": 1.2
      },
      {
        "time_bucket": "180-300",
        "em_bucket": "(2.034, 2.897]",
        "mult": 1.15
      }
    ]
  }
]
