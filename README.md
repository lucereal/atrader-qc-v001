# Simple Short Iron Condor Strategy 

Made in QuantConnect. The algorithm runs fully on historic data. It sells iron condors to generate premium. 

The algorithm has technical filters RSI, VWAP, ATR, BB, and more. It has option choosing criteria using spread, delta, IV. 

The algorithm has to be refined using the criteria for choosing options and for no trade days.

The research section has evaluations on which criteria results in best profit, expectancy, tail ratios, etc. 

The algorithm most recently was made to cast a wide net to just collect data without filters and criteria using standard contracts. This is to help the research. 


The next phase of the algo is to refine and make profitable before turning on. 