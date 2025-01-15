query = """
    query CoverdCallStrategy($after: String, $first: Int, $orderBy: String, $baseSecurity_Ticker_In: [String], $data_Delta_Gte: Float, $endDate_Gte: Date, $endDate_Lte: Date, $strickPriceDiffWithBasePriceRange: RangeInput, $coverCallGte: Int, $coverCallFinalPriceDiffPercentByBasePriceRange: RangeInput, $coverCallVolumeGte: BigInt) {
      options(
        after: $after
        first: $first
        orderBy: $orderBy
        baseSecurity_Ticker_In: $baseSecurity_Ticker_In
        data_Delta_Gte: $data_Delta_Gte
        endDate_Gte: $endDate_Gte
        endDate_Lte: $endDate_Lte
        hasCoverCall: true
        strickPriceDiffWithBasePriceRange: $strickPriceDiffWithBasePriceRange
        coverCallGte: $coverCallGte
        optionType: BUY
        coverCallFinalPriceDiffPercentByBasePriceRange: $coverCallFinalPriceDiffPercentByBasePriceRange
        coverCallVolumeGte: $coverCallVolumeGte
      ) {
        edges {
          node {
            id
            finalPriceDiffPercentByFinalPrice
            coverCallFinalPriceDiffPercentByBasePrice
            security {
              symbol
              id
              orderBook {
                highestBidPrice
                lowestAskPrice
                highestBidValue
              }
            }
            strickPrice
            coverCallFinalPrice
            coverCallVolume
            coverCall
            coverCallProfit
            coverCallInEndDate
            baseSecurity {
              symbol
              orderBook {
                lowestAskPrice
              }
            }
            endDate
            data {
              delta
            }
            guarantee
          }
        }
      }
    }
"""
