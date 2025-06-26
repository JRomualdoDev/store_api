from typing import List, Optional
from uuid import UUID
from bson import Decimal128
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import pymongo
from store.db.mongo import db_client
from store.models.product import ProductModel
from store.schemas.product import (
    ProductFilter,
    ProductIn,
    ProductOut,
    ProductUpdate,
    ProductUpdateOut,
    convert_decimal_128,
)
from store.core.exceptions import NotFoundException


class ProductUsecase:
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient = db_client.get()
        self.database: AsyncIOMotorDatabase = self.client.get_database()
        self.collection = self.database.get_collection("products")

    async def create(self, body: ProductIn) -> ProductOut:
        product_model = ProductModel(**body.model_dump())
        await self.collection.insert_one(product_model.model_dump())

        return ProductOut(**product_model.model_dump())

    async def get(self, id: UUID) -> ProductOut:
        result = await self.collection.find_one({"id": id})

        if not result:
            raise NotFoundException(message=f"Product not found with filter: {id}")

        return ProductOut(**result)

    async def query(self, filter: ProductFilter) -> List[ProductOut]:

        filter_dict = {}

        if filter.min_price is not None:
            filter_dict["price"] = {"$gte": convert_decimal_128(str(filter.min_price))}

        if filter.max_price is not None:
            if "price" in filter_dict:
                filter_dict["price"]["$lte"] = convert_decimal_128(
                    str(filter.max_price)
                )
            else:
                filter_dict["price"] = {
                    "$lte": convert_decimal_128(str(filter.max_price))
                }

        return [ProductOut(**item) async for item in self.collection.find(filter_dict)]

    async def update(self, id: UUID, body: ProductUpdate) -> ProductUpdateOut:
        result = await self.collection.find_one_and_update(
            filter={"id": id},
            update={"$set": body.model_dump(exclude_none=True)},
            return_document=pymongo.ReturnDocument.AFTER,
        )

        if not result:
            raise NotFoundException(message=f"Product not found for update")

        return ProductUpdateOut(**result)

    async def delete(self, id: UUID) -> bool:
        product = await self.collection.find_one({"id": id})
        if not product:
            raise NotFoundException(message=f"Product not found with filter: {id}")

        result = await self.collection.delete_one({"id": id})

        return True if result.deleted_count > 0 else False


product_usecase = ProductUsecase()
