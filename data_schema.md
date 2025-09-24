--- data schema ---
1. videos
{
  "settings": {
    "index": { "number_of_shards": 1, "number_of_replicas": 0 }
  },
  "mappings": {
    "properties": {
      "video_id":        { "type": "keyword" },
      "title":           { "type": "text"    },
      "description":     { "type": "text"    },
      "published_at":    { "type": "date"    },
      "channel_id":      { "type": "keyword" },
      "tags":            { "type": "keyword" },
      "places":          { "type": "keyword" },  // place_id 목록
      "place_names":     { "type": "text"    },  // 검색 편의용
      "sentiment_score": { "type": "float"   },
      "views":           { "type": "long"    },
      "likes":           { "type": "long"    }
    }
  }
}

2. places
{
  "settings": { "index": { "number_of_shards": 1, "number_of_replicas": 0 } },
  "mappings": {
    "properties": {
      "place_id":     { "type": "keyword" },
      "name":         { "type": "text"    },
      "country_code": { "type": "keyword" },
      "admin1":       { "type": "keyword" },
      "admin2":       { "type": "keyword" },
      "location":     { "type": "geo_point" }
    }
  }
}
