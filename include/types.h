#ifndef SEQ_TYPES_H
#define SEQ_TYPES_H

#include <string>
#include <map>
#include "llvm.h"
#include "seqdata.h"
#include "exc.h"
#include "util.h"

namespace seq {
	namespace types {
		class Type {
		private:
			Type *parent;
			SeqData key;
		protected:
			llvm::Function *printFunc;
			std::string printName;
			void *print;
		public:
			Type(Type *parent, SeqData key, std::string printName, void *print);
			Type(Type *parent, SeqData key);
			Type(Type *parent);

			virtual llvm::Type *getLLVMType(llvm::LLVMContext& context)=0;

			virtual void callPrint(std::shared_ptr<std::map<SeqData, llvm::Value *>> outs, llvm::BasicBlock *block);

			virtual void finalizePrint(llvm::ExecutionEngine *eng);

			bool isChildOf(Type *type)
			{
				return (this == type) || (parent && parent->isChildOf(type));
			}

			SeqData getKey() const
			{
				return key;
			}
		};

		class Base : public Type {
		private:
			Base() : Type(nullptr) {};
		public:
			Base(Base const&)=delete;
			void operator=(Base const&)=delete;

			llvm::Type *getLLVMType(llvm::LLVMContext& context) override
			{
				throw exc::SeqException("cannot instantiate base class");
			}

			static Base *get()
			{
				static Base instance;
				return &instance;
			}
		};

		class Void : public Type {
		private:
			Void() : Type(nullptr) {};
		public:
			Void(Void const&)=delete;
			void operator=(Void const&)=delete;

			llvm::Type *getLLVMType(llvm::LLVMContext& context) override
			{
				return llvm::Type::getVoidTy(context);
			}

			static Void *get()
			{
				static Void instance;
				return &instance;
			}
		};

		class Seq : public Type {
		private:
			Seq() : Type(Base::get(), SeqData::SEQ, "print", (void *)&util::print) {};
		public:
			Seq(Seq const&)=delete;
			void operator=(Seq const&)=delete;

			llvm::Type *getLLVMType(llvm::LLVMContext& context) override
			{
				return llvm::Type::getInt8Ty(context);
			}

			void callPrint(std::shared_ptr<std::map<SeqData, llvm::Value *>> outs, llvm::BasicBlock *block) override;

			static Seq *get()
			{
				static Seq instance;
				return &instance;
			}
		};

		template<unsigned K>
		class Mer : public Type {
		private:
			Mer() : Type(Seq::get(), SeqData::SEQ, "print", (void *)&util::print) {};
		public:
			Mer(Mer const&)=delete;
			void operator=(Mer const&)=delete;

			llvm::Type *getLLVMType(llvm::LLVMContext& context) override
			{
				return llvm::IntegerType::getIntNTy(context, 2*K);
			}

			static Mer *get()
			{
				static Mer<K> instance;
				return &instance;
			}
		};

		class Number : public Type {
		private:
			Number() : Type(Base::get()) {};
		public:
			Number(Number const&)=delete;
			void operator=(Number const&)=delete;

			llvm::Type *getLLVMType(llvm::LLVMContext& context) override
			{
				throw exc::SeqException("cannot instantiate number class");
			}

			static Number *get()
			{
				static Number instance;
				return &instance;
			}
		};

		class Int : public Type {
		private:
			Int() : Type(Number::get(), SeqData::INT, "print_int", (void *)&util::print_int) {};
		public:
			Int(Int const&)=delete;
			void operator=(Int const&)=delete;

			llvm::Type *getLLVMType(llvm::LLVMContext& context) override
			{
				return llvm::IntegerType::getInt32Ty(context);
			}

			static Int *get()
			{
				static Int instance;
				return &instance;
			}
		};

		class Float : public Type {
		private:
			Float() : Type(Number::get(), SeqData::DOUBLE, "print_double", (void *)&util::print_double) {};
		public:
			Float(Float const&)=delete;
			void operator=(Float const&)=delete;

			llvm::Type *getLLVMType(llvm::LLVMContext& context) override
			{
				return llvm::IntegerType::getInt32Ty(context);
			}

			static Float *get()
			{
				static Float instance;
				return &instance;
			}
		};

		template<typename BASE, unsigned COUNT>
		class Array : public Type {
		private:
			Array() : Type(Base::get(), SeqData::ARRAY) {}
		public:
			Array(Array const&)=delete;
			void operator=(Array const&)=delete;

			llvm::Type *getLLVMType(llvm::LLVMContext& context) override
			{
				return llvm::ArrayType::get(BASE().getLLVMType(context), COUNT);
			}

			static Array *get()
			{
				static Array<BASE,COUNT> instance;
				return &instance;
			}
		};
	}
}

#endif /* SEQ_TYPES_H */
