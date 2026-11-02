"""Index review events consumed from Kafka."""
import asyncio
import json
import os
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from app import ElasticsearchReviewIndex

async def main():
    broker=os.environ.get('KAFKA_BOOTSTRAP_SERVERS','kafka:9092')
    consumer=AIOKafkaConsumer('reviews.created',bootstrap_servers=broker,group_id='review-analytics',auto_offset_reset='earliest',enable_auto_commit=False)
    producer=AIOKafkaProducer(bootstrap_servers=broker)
    await consumer.start(); await producer.start()
    try:
        async for message in consumer:
            review=json.loads(message.value.decode('utf-8'))
            await asyncio.to_thread(ElasticsearchReviewIndex().index,review)
            result={'review_id':review['review_id'],'index':'clinic-reviews'}
            await producer.send_and_wait('reviews.indexed',json.dumps(result,ensure_ascii=False).encode('utf-8'),key=review['review_id'].encode('utf-8'))
            await consumer.commit()
            print(json.dumps(result),flush=True)
    finally:
        await consumer.stop(); await producer.stop()

if __name__=='__main__': asyncio.run(main())
